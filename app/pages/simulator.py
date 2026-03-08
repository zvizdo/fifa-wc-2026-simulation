"""
Simulator page — Adjust team FIFA ranks and run custom simulations.
Compare results against the 100,000-simulation baseline.
"""
import os
import sys
import copy
import json
import math
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

import streamlit as st
import duckdb

# Ensure engine is importable
_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.sim import Competition
from engine.match import ModeledMatch
from sim_worker import run_single_sim

from ui.cards import render_info_box
from ui.flags import get_flag
from ui.simulator_components import (
    render_shift_badge,
    render_score_shift_badge,
    render_podium_with_shifts,
    render_champion_shifts_table,
    render_sim_group_table,
    render_team_progression_table,
)
from ui.headlines import generate_headlines
from db.simulator_queries import (
    get_user_champion_probs,
    get_user_runner_up_probs,
    get_user_third_place_probs,
    get_user_group_standings,
    get_user_stage_reach_probs,
    get_user_all_team_best_finish,
)
from db.landing_queries import (
    get_champion_probs,
    get_runner_up_probs,
    get_third_place_probs,
    get_baseline_all_team_best_finish
)
from db.team_queries import get_team_stage_reach_probs
from db.competition_queries import get_all_groups_most_likely
from config import SIMULATOR_NUM_SIMS, SIMULATOR_BASE_SEED, GROUP_NAMES

import pickle
from pathlib import Path
import math

# ── Advantage slider config ──────────────────────────────────────────────────

# 9-step multipliers: position 4 (index 3) = Normal = trained value
ADVANTAGE_MULTIPLIERS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
ADVANTAGE_LABELS = ["None", "Minimal", "Small", "Medium", "Normal", "Boosted", "Large", "Strong", "Extreme"]
ADVANTAGE_DEFAULT_IDX = 4  # "Normal"

def _load_trained_discounts():
    """Read the trained host_discount and confed_discount from the model."""
    model_path = Path(_ROOT) / "model" / "expanded_model.pkl"
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)
    transformer = artifact["pipeline"].steps[0][1]
    return transformer.host_discount, transformer.confed_discount

# ── Helpers ──────────────────────────────────────────────────────────────────

def is_stat_sig_prop(user_prob, base_prob, num_sims):
    """Check statistical significance for proportions (percentages 0-100)."""
    p_hat = user_prob / 100.0
    p_0 = base_prob / 100.0
    if p_0 == 0 or p_0 == 1:
        return p_hat != p_0
        
    se = math.sqrt((p_0 * (1 - p_0)) / num_sims)
    if se == 0:
        return False
        
    z = (p_hat - p_0) / se
    return abs(z) > 1.96

def is_stat_sig_mean(user_mean, base_mean, user_sd, num_sims):
    """Check statistical significance for means using z-test approximation."""
    if pd.isna(user_sd) or user_sd == 0 or num_sims == 0:
        return user_mean != base_mean
    t = (user_mean - base_mean) / (user_sd / math.sqrt(num_sims))
    return abs(t) > 1.96

_TEAMS_JSON = os.path.join(_ROOT, "data", "wc_2026_teams.json")

def _init_state():
    """Load teams JSON and initialize session state on first visit."""
    if "sim_default_ranks" in st.session_state:
        return

    with open(_TEAMS_JSON) as f:
        teams_data = json.load(f)

    raw_ranks: dict[str, int] = {}
    team_meta: dict[str, dict] = {}

    for group_name, group_teams in teams_data["groups"].items():
        for t in group_teams:
            name = t["name"]
            raw_ranks[name] = t["fifa_rank"]
            team_meta[name] = {
                "group": group_name,
                "confederation": t["confederation"],
                "host": t.get("host", False),
            }

    # Resolve duplicate FIFA ranks so every team starts with a unique rank.
    # Without this, the first slider change triggers _rebuild_ranks which
    # resolves duplicates and causes spurious shifts for uninvolved teams.
    sorted_teams = sorted(raw_ranks.items(), key=lambda x: (x[1], x[0]))
    default_ranks: dict[str, int] = {}
    occupied: set[int] = set()
    for team, raw_rank in sorted_teams:
        slot = raw_rank
        while slot in occupied:
            slot += 1
        default_ranks[team] = slot
        occupied.add(slot)

    st.session_state["sim_teams_data"] = teams_data
    st.session_state["sim_default_ranks"] = default_ranks
    st.session_state["sim_adjusted_ranks"] = dict(default_ranks)
    st.session_state["sim_user_overrides"] = {}  # only explicit slider changes
    st.session_state["sim_team_meta"] = team_meta
    st.session_state["sim_expanded_team"] = None
    st.session_state["sim_has_results"] = False
    st.session_state["sim_user_db"] = None

    # Advantage slider defaults
    st.session_state["sim_host_adv_idx"] = ADVANTAGE_DEFAULT_IDX
    st.session_state["sim_confed_adv_idx"] = ADVANTAGE_DEFAULT_IDX

    # Cache trained discount values for display
    host_d, confed_d = _load_trained_discounts()
    st.session_state["sim_trained_host_discount"] = host_d
    st.session_state["sim_trained_confed_discount"] = confed_d


def _rebuild_ranks():
    """Rebuild all ranks from defaults + explicit user overrides, resolving collisions.

    Strategy: lock overridden teams at their chosen ranks, then reassign all
    non-overridden teams into the remaining free slots, preserving their
    relative default-rank order.  This avoids chain-cascade bugs and
    guarantees every team gets a unique rank in [1, N].
    """
    defaults = st.session_state["sim_default_ranks"]
    overrides = st.session_state.setdefault("sim_user_overrides", {})

    ranks: dict[str, int] = {}
    occupied: set[int] = set()

    # 1. Lock overridden teams at their chosen ranks
    for team, rank in overrides.items():
        ranks[team] = rank
        occupied.add(rank)

    # 2. Non-overridden teams sorted by their default rank (best first)
    free_teams = sorted(
        (t for t in defaults if t not in overrides),
        key=lambda t: defaults[t],
    )

    # 3. Assign each to the nearest free slot at or after its default rank
    next_slot = 1
    for team in free_teams:
        target = defaults[team]
        slot = max(target, next_slot)
        while slot in occupied:
            slot += 1
        ranks[team] = slot
        occupied.add(slot)
        next_slot = slot + 1

    st.session_state["sim_adjusted_ranks"] = ranks

    # Sync slider widget keys so they reflect cascaded values.
    # Without this, Streamlit ignores the `value` param on re-render
    # and shows the stale session_state[key] instead.
    for team, rank in ranks.items():
        slider_key = f"sim_slider_{team}"
        if slider_key in st.session_state:
            st.session_state[slider_key] = rank


def _has_any_changes() -> bool:
    """Return True if any rank or advantage slider differs from defaults."""
    adj = st.session_state["sim_adjusted_ranks"]
    dfl = st.session_state["sim_default_ranks"]
    rank_changed = any(adj[t] != dfl[t] for t in adj)
    adv_changed = (
        st.session_state["sim_host_adv_idx"] != ADVANTAGE_DEFAULT_IDX
        or st.session_state["sim_confed_adv_idx"] != ADVANTAGE_DEFAULT_IDX
    )
    return rank_changed or adv_changed


def _get_changes() -> list[tuple[str, int, int]]:
    """Return (team, old_rank, new_rank) for all changed teams."""
    adj = st.session_state["sim_adjusted_ranks"]
    dfl = st.session_state["sim_default_ranks"]
    return [(t, dfl[t], adj[t]) for t in sorted(adj) if adj[t] != dfl[t]]


def _build_modified_teams_data() -> dict:
    """Deep-copy original JSON, overwrite fifa_rank values."""
    data = copy.deepcopy(st.session_state["sim_teams_data"])
    adj = st.session_state["sim_adjusted_ranks"]
    for group_teams in data["groups"].values():
        for t in group_teams:
            t["fifa_rank"] = adj[t["name"]]
    return data


def _run_simulation():
    """Run N simulations in parallel, store results in an in-memory DuckDB."""
    teams_data = _build_modified_teams_data()
    num_sims = SIMULATOR_NUM_SIMS

    # Close previous DB if any
    if st.session_state.get("sim_user_db"):
        try:
            st.session_state["sim_user_db"].close()
        except Exception:
            pass

    con = duckdb.connect(":memory:")

    # Create schema (mirrors Competition.init_db)
    con.execute("""
        CREATE TABLE matches (
            sim_id VARCHAR NOT NULL, match_number INTEGER NOT NULL,
            stage VARCHAR NOT NULL, group_name VARCHAR,
            home_team VARCHAR NOT NULL, away_team VARCHAR NOT NULL,
            home_score INTEGER, away_score INTEGER, winner VARCHAR,
            city VARCHAR, stadium VARCHAR, country VARCHAR,
            PRIMARY KEY (sim_id, match_number))
    """)
    con.execute("""
        CREATE TABLE group_standings (
            sim_id VARCHAR NOT NULL, group_name VARCHAR NOT NULL,
            position INTEGER NOT NULL, team VARCHAR NOT NULL,
            confederation VARCHAR NOT NULL, fifa_rank INTEGER NOT NULL,
            played INTEGER NOT NULL, wins INTEGER NOT NULL,
            draws INTEGER NOT NULL, losses INTEGER NOT NULL,
            goals_for INTEGER NOT NULL, goals_against INTEGER NOT NULL,
            goal_difference INTEGER NOT NULL, points INTEGER NOT NULL,
            advanced BOOLEAN NOT NULL,
            PRIMARY KEY (sim_id, group_name, position))
    """)
    con.execute("""
        CREATE TABLE third_place_ranks (
            sim_id VARCHAR NOT NULL, rank INTEGER NOT NULL,
            team VARCHAR NOT NULL, group_name VARCHAR NOT NULL,
            points INTEGER NOT NULL, goal_difference INTEGER NOT NULL,
            goals_for INTEGER NOT NULL, advanced BOOLEAN NOT NULL,
            PRIMARY KEY (sim_id, rank))
    """)

    progress = st.progress(0, text="Preparing simulation...")

    total_cpus = os.cpu_count() or 4
    num_workers = max(2, int(total_cpus / 2) - 1)
    # Build match_kwargs from advantage sliders
    host_mul = ADVANTAGE_MULTIPLIERS[st.session_state["sim_host_adv_idx"]]
    confed_mul = ADVANTAGE_MULTIPLIERS[st.session_state["sim_confed_adv_idx"]]
    match_kwargs = {}
    if host_mul != 1.0:
        match_kwargs["host_discount_mul"] = host_mul
    if confed_mul != 1.0:
        match_kwargs["confed_discount_mul"] = confed_mul

    tasks = [(teams_data, i, match_kwargs) for i in range(num_sims)]
    
    completed = 0
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(run_single_sim, task) for task in tasks]
        for future in as_completed(futures):
            match_rows, stand_rows, third_rows = future.result()
            Competition.insert_rows(con, match_rows, stand_rows, third_rows)
            completed += 1
            progress.progress(completed / num_sims, text=f"Simulating... {completed}/{num_sims}")

    Competition.create_db_indexes(con)
    progress.progress(1.0, text="Simulation complete!")

    st.session_state["sim_user_db"] = con
    st.session_state["sim_has_results"] = True


# ── Result views ─────────────────────────────────────────────────────────────


def _render_headlines_view(user_db, num_sims):
    """Dynamic headlines based on statistical significance."""

    render_info_box(
        "<strong>How to read this:</strong> "
        f"We compare your {SIMULATOR_NUM_SIMS} simulations to the 100k baseline "
        "using a <strong>p &lt; 0.05</strong> threshold to filter out noise. <br><br>"
        "<strong>Bold blue and bold red shifts</strong> are statistically significant. "
        "<strong>Faded shifts</strong> are within expected variance. "
        "For example: a bold <span class='wc-shift-positive' style='font-weight:bold;'>+4.0%</span> represents a mathematically proven shift, "
        "while a faded <span class='wc-shift-positive' style='opacity: 0.6; font-size: 0.85em;'>+1.2%</span> could just be simulation noise."
    )

    overrides = st.session_state.get("sim_user_overrides", {})
    headlines = generate_headlines(user_db, num_sims, overrides, max_headlines=6)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="wc-section-sub">Data-Driven Headlines</div>', unsafe_allow_html=True)

    if not headlines:
        st.info("No statistically significant shifts detected. Try making larger rank adjustments to see meaningful impacts.")
    else:
        for h in headlines:
            st.markdown(
                f"<div style='margin-bottom:0.8rem; font-size:1.05rem;'>"
                f"<strong>{h.emoji} {h.label}:</strong> {h.html}</div>",
                unsafe_allow_html=True,
            )

    # Collect unique teams from headlines for stats section
    highlighted_teams = []
    seen = set()
    for h in headlines:
        for t in h.teams:
            if t not in seen:
                highlighted_teams.append(t)
                seen.add(t)

    if highlighted_teams:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="wc-section-sub">Headline Team Stats</div>', unsafe_allow_html=True)
        for team in highlighted_teams:
            user_stages = get_user_stage_reach_probs(user_db, num_sims, team)
            base_stages = get_team_stage_reach_probs(team)
            flag = get_flag(team)
            with st.expander(f"{flag} {team} Stage-by-Stage Breakdown", expanded=False):
                stage_order = [
                    ("GROUP_STAGE", "Group Stage"),
                    ("ROUND_OF_32", "Round of 32"),
                    ("ROUND_OF_16", "Round of 16"),
                    ("QUARTER_FINALS", "Quarter-Finals"),
                    ("SEMI_FINALS", "Semi-Finals"),
                    ("FINAL", "Final"),
                    ("CHAMPION", "Champion"),
                ]

                baseline_dict = dict(zip(base_stages["stage"], base_stages["probability"]))

                html = '<table class="wc-sim-results-table"><thead><tr>'
                html += '<th>Stage</th><th>Your Sim</th><th>Baseline</th><th>Shift</th>'
                html += '</tr></thead><tbody>'

                for stage_key, display in stage_order:
                    user_row = user_stages[user_stages["stage"] == stage_key]
                    u_prob = float(user_row["probability"].iloc[0]) if not user_row.empty else 0.0
                    b_prob = baseline_dict.get(stage_key, 0.0)
                    s = u_prob - b_prob

                    is_sig = False if stage_key == "GROUP_STAGE" else is_stat_sig_prop(u_prob, b_prob, num_sims)
                    shift_html = render_shift_badge(s, is_sig)

                    html += '<tr>'
                    html += f'<td>{display}</td>'
                    html += f'<td><strong>{u_prob:.1f}%</strong></td>'
                    html += f'<td>{b_prob:.1f}%</td>'
                    html += f'<td>{shift_html}</td>'
                    html += '</tr>'

                html += '</tbody></table>'
                st.markdown(html, unsafe_allow_html=True)


def _render_groups_view(user_db, num_sims):
    """Group finishing orders with position shift indicators."""

    render_info_box(
        "<strong>How to read this:</strong> "
        "Most likely finishing order per group from your simulation. <br><br>"
        "<strong>Bold blue and bold red shifts</strong> mean a team's finishing position changed with statistical significance. "
        "<strong>Faded shifts</strong> are within expected variance. "
        "For example: a bold <span class='wc-shift-positive' style='font-weight:bold;'>+1</span> means the team consistently finishes higher, "
        "while a faded <span class='wc-shift-positive' style='opacity: 0.6; font-size: 0.85em;'>+1</span> is mathematically indistinguishable from the baseline."
    )

    baseline_groups = get_all_groups_most_likely()
    baseline_orders = {}
    for _, row in baseline_groups.iterrows():
        baseline_orders[row["group_name"]] = row["team_order"].split(",")

    user_finish = get_user_all_team_best_finish(user_db, num_sims)
    baseline_finish = get_baseline_all_team_best_finish()
    is_sig_dict = {}
    base_score_dict = dict(zip(baseline_finish["team"], baseline_finish["avg_stage_score"]))
    for _, row in user_finish.iterrows():
        team = row["team"]
        user_sc = row["avg_stage_score"]
        user_sd = row["stddev_stage_score"]
        base_sc = base_score_dict.get(team, 0.0)
        is_sig = is_stat_sig_mean(user_sc, base_sc, user_sd, num_sims)
        is_sig_dict[team] = is_sig

    for row_start in range(0, 12, 3):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            grp_idx = row_start + i
            if grp_idx >= 12:
                break
            group_name = GROUP_NAMES[grp_idx]
            with col:
                standings = get_user_group_standings(user_db, num_sims, group_name)
                base_order = baseline_orders.get(group_name, [])
                if standings:
                    render_sim_group_table(standings, base_order, group_name, is_sig_dict)


def _render_teams_view(user_db, num_sims):
    """Per-team progression view sorted by biggest positive shift."""

    render_info_box(
        "<strong>How to read this:</strong> "
        "Filtered to show <strong>ONLY teams with statistically significant shifts</strong> "
        "in their Tournament Depth (p &lt; 0.05). "
        "Tournament Depth calculates expected progression (Group Stage = 0, R32 = 1 ... Winner = 6). A higher score means a deeper run.<br><br>"
        "<strong>Bold blue and bold red</strong> shifts indicate a mathematically significant change, "
        "while <strong>faded</strong> shifts are within expected variance. "
        "For example: a bold <span class='wc-shift-positive' style='font-weight:bold;'>+0.50</span> Tournament Depth shift means the team improved, "
        "while a faded <span class='wc-shift-positive' style='opacity: 0.6; font-size: 0.85em;'>+0.10</span> is just statistical noise."
    )

    user_finish = get_user_all_team_best_finish(user_db, num_sims)
    baseline_finish = get_baseline_all_team_best_finish()
    
    base_champ_dict = dict(zip(baseline_finish["team"], baseline_finish["champ_prob"]))
    base_score_dict = dict(zip(baseline_finish["team"], baseline_finish["avg_stage_score"]))

    team_list = []
    for _, row in user_finish.iterrows():
        team = row["team"]
        user_champ = row["champ_prob"]
        base_champ = base_champ_dict.get(team, 0.0)
        user_score = row["avg_stage_score"]
        user_sd = row["stddev_stage_score"]
        base_score = base_score_dict.get(team, 0.0)
        
        is_sig = is_stat_sig_mean(user_score, base_score, user_sd, num_sims)
        if is_sig:
            team_list.append({
                "team": team,
                "user_champ": user_champ,
                "base_champ": base_champ,
                "champ_shift": user_champ - base_champ,
                "champ_is_sig": is_stat_sig_prop(user_champ, base_champ, num_sims),
                "avg_score": user_score,
                "avg_score_shift": user_score - base_score,
                "is_sig": is_sig,
            })

    if not team_list:
        st.info("No statistically significant shifts detected. All changes were within margins of expected variance.")
        return

    team_list.sort(key=lambda d: abs(d["avg_score_shift"]), reverse=True)

    html = '<div class="wc-card-flat" style="padding:0.75rem;">'
    html += '<table class="wc-sim-results-table"><thead><tr>'
    html += '<th>#</th><th>Team</th><th>Champion %</th><th>Baseline</th><th>Shift</th><th>Tournament Depth</th><th>Shift</th>'
    html += '</tr></thead><tbody>'

    for rank, t in enumerate(team_list[:15], 1):
        flag = get_flag(t["team"])
        champ_shift_badge = render_shift_badge(t["champ_shift"], t["champ_is_sig"])
        score_shift_badge = render_score_shift_badge(t["avg_score_shift"], True) # filtered to sig only
        
        html += '<tr>'
        html += f'<td>{rank}</td>'
        html += f'<td>{flag} {t["team"]}</td>'
        html += f'<td><strong>{t["user_champ"]:.1f}%</strong></td>'
        html += f'<td>{t["base_champ"]:.1f}%</td>'
        html += f'<td>{champ_shift_badge}</td>'
        html += f'<td><strong>{t["avg_score"]:.2f}</strong></td>'
        html += f'<td>{score_shift_badge}</td>'
        html += '</tr>'

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="wc-section-sub">Stage-by-Stage Breakdown for Impacted Teams</div>',
        unsafe_allow_html=True,
    )

    for t in team_list:
        team = t["team"]
        flag = get_flag(team)
        shift = t["champ_shift"]

        # Include shift in the expander label
        if shift > 0.05:
            shift_text = f" | Shift: +{shift:.1f}%"
        elif shift < -0.05:
            shift_text = f" | Shift: {shift:.1f}%"
        else:
            shift_text = ""

        label = (
            f"{flag} {team} — Champion: {t['user_champ']:.1f}%"
            f"{shift_text}"
        )

        auto_expand = shift > 2.0
        with st.expander(label, expanded=auto_expand):
            user_stages = get_user_stage_reach_probs(user_db, num_sims, team)
            baseline_stages = get_team_stage_reach_probs(team)
            render_team_progression_table(team, user_stages, baseline_stages, num_sims)


# ── Page layout ──────────────────────────────────────────────────────────────


_init_state()

st.markdown(
    '<div class="wc-section-header">Simulator</div>',
    unsafe_allow_html=True,
)

render_info_box(
    "Adjust team FIFA rankings and run your own simulations to see how "
    "probabilities shift compared to the 100,000-simulation baseline. "
    "Change any team's rank or tweak the advantage sliders below, hit "
    "<strong>Run Simulation</strong>, and explore the results."
)

# ── Advantage sliders ────────────────────────────────────────────────────────

st.markdown(
    '<div class="wc-section-sub">Model Advantage Settings</div>',
    unsafe_allow_html=True,
)

trained_host = st.session_state["sim_trained_host_discount"]
trained_confed = st.session_state["sim_trained_confed_discount"]

render_info_box(
    "These sliders let you scale the model's learned advantages. "
    "<strong>Normal</strong> uses the value the model learned from 1,400+ historical matches. "
    "Move left to reduce the effect, or right to amplify it.<br><br>"
    "<strong>Host Nation Advantage</strong> — Host teams historically perform better "
    f"(the model learned a <strong>{trained_host:.0%}</strong> rank boost). "
    "This affects the 3 co-hosts: USA, Canada, and Mexico.<br>"
    "<strong>Strong Confederation Advantage</strong> — UEFA and CONMEBOL teams "
    f"receive a smaller edge (learned: <strong>{trained_confed:.0%}</strong> rank boost) "
    "reflecting historically stronger competition within those federations."
)

adv_col1, adv_col2 = st.columns(2)

with adv_col1:
    host_idx = st.select_slider(
        "🏟️ Host Nation Advantage",
        options=list(range(len(ADVANTAGE_LABELS))),
        value=st.session_state["sim_host_adv_idx"],
        format_func=lambda i: ADVANTAGE_LABELS[i],
        key="sim_host_adv_slider",
    )
    st.session_state["sim_host_adv_idx"] = host_idx
    host_mul = ADVANTAGE_MULTIPLIERS[host_idx]
    if host_idx != ADVANTAGE_DEFAULT_IDX:
        effective = trained_host * host_mul
        st.caption(f"Effective boost: {effective:.0%} (trained: {trained_host:.0%} × {host_mul:.2f})")

with adv_col2:
    confed_idx = st.select_slider(
        "⚽ Strong Confederation Advantage",
        options=list(range(len(ADVANTAGE_LABELS))),
        value=st.session_state["sim_confed_adv_idx"],
        format_func=lambda i: ADVANTAGE_LABELS[i],
        key="sim_confed_adv_slider",
    )
    st.session_state["sim_confed_adv_idx"] = confed_idx
    confed_mul = ADVANTAGE_MULTIPLIERS[confed_idx]
    if confed_idx != ADVANTAGE_DEFAULT_IDX:
        effective = trained_confed * confed_mul
        st.caption(f"Effective boost: {effective:.0%} (trained: {trained_confed:.0%} × {confed_mul:.2f})")

# ── Rank adjustment UI ───────────────────────────────────────────────────────

st.markdown(
    '<div class="wc-section-sub">Adjust Team Rankings</div>',
    unsafe_allow_html=True,
)
st.caption("Click a team row to expand and adjust their FIFA rank. Ranks cascade down on collision.")

adjusted = st.session_state["sim_adjusted_ranks"]
defaults = st.session_state["sim_default_ranks"]
meta = st.session_state["sim_team_meta"]

# Show active changes summary
changes = _get_changes()
if changes:
    html = '<div class="wc-sim-changes-summary">'
    html += '<div style="font-weight:600; margin-bottom:0.3rem;">Active Changes:</div>'
    for team, old, new in changes:
        flag = get_flag(team)
        color = "var(--wc-turquoise)" if new < old else "var(--wc-magenta)"
        html += (
            f'<span class="change-item">'
            f'{flag} {team}: {old} &rarr; {new} '
            f'<span style="color:{color}; font-weight:600;">({new - old:+d})</span>'
            f'</span>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# Group selector and single group compact table layout
teams_data = st.session_state["sim_teams_data"]

selected_group = st.selectbox(
    "Select Group to Edit",
    options=GROUP_NAMES,
    format_func=lambda x: f"Group {x}",
    key="sim_group_selector"
)

group_teams = teams_data["groups"][selected_group]

# Build compact table for selected group
html = '<div class="wc-card-flat" style="padding:0.4rem 0.5rem; max-width: 400px; margin-bottom: 1rem;">'
html += '<table class="wc-group-table"><thead><tr>'
html += '<th>Team</th><th>Rank</th>'
html += '</tr></thead><tbody>'

for t in group_teams:
    team_name = t["name"]
    flag = get_flag(team_name)
    current_rank = adjusted[team_name]
    default_rank = defaults[team_name]
    is_changed = current_rank != default_rank

    if is_changed:
        diff = current_rank - default_rank
        if diff < 0:
            rank_html = (
                f'<strong>{current_rank}</strong> '
                f'<span class="wc-shift-positive">({diff:+d})</span>'
            )
        else:
            rank_html = (
                f'<strong>{current_rank}</strong> '
                f'<span class="wc-shift-negative">({diff:+d})</span>'
            )
        row_class = "advanced"
    else:
        rank_html = str(current_rank)
        row_class = ""

    html += f'<tr class="{row_class}">'
    html += f'<td>{flag} {team_name}</td>'
    html += f'<td>{rank_html}</td>'
    html += '</tr>'

html += '</tbody></table></div>'
st.markdown(html, unsafe_allow_html=True)

# Expander for adjusting ranks within this group
def _on_rank_change(t_name):
    new_r = st.session_state[f"sim_slider_{t_name}"]
    defaults = st.session_state["sim_default_ranks"]
    overrides = st.session_state.setdefault("sim_user_overrides", {})

    # Track only explicit user changes; remove if back to default
    if new_r == defaults[t_name]:
        overrides.pop(t_name, None)
    else:
        overrides[t_name] = new_r

    _rebuild_ranks()
    st.session_state["sim_expanded_team"] = t_name

for t in group_teams:
    team_name = t["name"]
    current_rank = adjusted[team_name]
    default_rank = defaults[team_name]
    is_changed = current_rank != default_rank
    flag = get_flag(team_name)

    change_text = f" ({current_rank - default_rank:+d})" if is_changed else ""
    exp_label = f"{flag} {team_name} — Rank {current_rank}{change_text}"

    with st.expander(exp_label, expanded=(st.session_state["sim_expanded_team"] == team_name)):
        tm = meta[team_name]
        host_text = " | Host" if tm["host"] else ""
        st.caption(f'{tm["confederation"]} | Default rank: {default_rank}{host_text}')

        _max_rank = max(100, max(adjusted.values()))
        st.slider(
            "FIFA Rank",
            min_value=1,
            max_value=_max_rank,
            value=current_rank,
            key=f"sim_slider_{team_name}",
            label_visibility="collapsed",
            on_change=_on_rank_change,
            args=(team_name,)
        )

# ── Action buttons ───────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)

col_run, col_reset = st.columns([2, 1])

with col_run:
    if st.button(
        f"Run Simulation ({SIMULATOR_NUM_SIMS} sims)",
        type="primary",
        use_container_width=True,
        disabled=not _has_any_changes(),
    ):
        _run_simulation()
        st.rerun()

with col_reset:
    if st.button("Reset All Ranks", use_container_width=True):
        st.session_state["sim_adjusted_ranks"] = dict(defaults)
        st.session_state["sim_user_overrides"] = {}
        st.session_state["sim_expanded_team"] = None
        st.session_state["sim_has_results"] = False
        st.session_state["sim_host_adv_idx"] = ADVANTAGE_DEFAULT_IDX
        st.session_state["sim_confed_adv_idx"] = ADVANTAGE_DEFAULT_IDX
        if st.session_state.get("sim_user_db"):
            try:
                st.session_state["sim_user_db"].close()
            except Exception:
                pass
            st.session_state["sim_user_db"] = None
        st.rerun()

# ── Results ──────────────────────────────────────────────────────────────────

if st.session_state.get("sim_has_results"):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="wc-section-header">Simulation Results</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"Comparing your {SIMULATOR_NUM_SIMS} simulations against the "
        f"100,000-simulation baseline."
    )

    results_view = st.pills(
        "View",
        options=["Headlines", "Groups", "Teams"],
        default="Headlines",
    )

    user_db = st.session_state["sim_user_db"]

    if results_view == "Headlines":
        _render_headlines_view(user_db, SIMULATOR_NUM_SIMS)
    elif results_view == "Groups":
        _render_groups_view(user_db, SIMULATOR_NUM_SIMS)
    elif results_view == "Teams":
        _render_teams_view(user_db, SIMULATOR_NUM_SIMS)
