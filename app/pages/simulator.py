"""
Simulator page — Adjust team FIFA ranks and run custom simulations.
Compare results against the 100,000-simulation baseline.
"""
import os
import sys
import copy
import json

import streamlit as st
import duckdb

# Ensure engine is importable
_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.sim import Competition
from engine.match import ModeledMatch

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


# ── Helpers ──────────────────────────────────────────────────────────────────


_TEAMS_JSON = os.path.join(_ROOT, "data", "wc_2026_teams.json")


def _init_state():
    """Load teams JSON and initialize session state on first visit."""
    if "sim_default_ranks" in st.session_state:
        return

    with open(_TEAMS_JSON) as f:
        teams_data = json.load(f)

    default_ranks: dict[str, int] = {}
    team_meta: dict[str, dict] = {}

    for group_name, group_teams in teams_data["groups"].items():
        for t in group_teams:
            name = t["name"]
            default_ranks[name] = t["fifa_rank"]
            team_meta[name] = {
                "group": group_name,
                "confederation": t["confederation"],
                "host": t.get("host", False),
            }

    st.session_state["sim_teams_data"] = teams_data
    st.session_state["sim_default_ranks"] = default_ranks
    st.session_state["sim_adjusted_ranks"] = dict(default_ranks)
    st.session_state["sim_team_meta"] = team_meta
    st.session_state["sim_expanded_team"] = None
    st.session_state["sim_has_results"] = False
    st.session_state["sim_user_db"] = None


def _cascade_rank(changed_team: str, new_rank: int):
    """Set *changed_team* to *new_rank* and cascade collisions downward."""
    ranks = st.session_state["sim_adjusted_ranks"]
    ranks[changed_team] = new_rank

    current_team = changed_team
    occupied = new_rank
    while True:
        collider = next(
            (t for t, r in ranks.items() if t != current_team and r == occupied),
            None,
        )
        if collider is None:
            break
        new_collider_rank = min(occupied + 1, 100)
        ranks[collider] = new_collider_rank
        if new_collider_rank >= 100:
            break
        current_team = collider
        occupied = new_collider_rank


def _has_rank_changes() -> bool:
    adj = st.session_state["sim_adjusted_ranks"]
    dfl = st.session_state["sim_default_ranks"]
    return any(adj[t] != dfl[t] for t in adj)


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
    """Run N simulations, store results in an in-memory DuckDB."""
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

    for i in range(num_sims):
        seed = SIMULATOR_BASE_SEED + i
        comp = Competition(teams_data=teams_data, random_seed=seed,
                           match_class=ModeledMatch)
        comp.simulate()
        match_rows, stand_rows, third_rows = comp.extract_rows(f"u{i}")
        Competition.insert_rows(con, match_rows, stand_rows, third_rows)

        progress.progress((i + 1) / num_sims,
                          text=f"Simulating... {i + 1}/{num_sims}")

    Competition.create_db_indexes(con)
    progress.progress(1.0, text="Simulation complete!")

    st.session_state["sim_user_db"] = con
    st.session_state["sim_has_results"] = True


# ── Result views ─────────────────────────────────────────────────────────────


def _render_podium_view(user_db, num_sims):
    """Top-3 podium + championship probability shifts table."""

    render_info_box(
        "<strong>How to read this:</strong> "
        "\"Your Sim\" shows results from your 100 custom simulations. "
        "\"Baseline\" shows the pre-computed 100k simulation results with default ranks. "
        "The <strong>shift</strong> indicates how your rank changes affected each team's chances."
    )

    user_champs = get_user_champion_probs(user_db, num_sims, limit=48)
    user_runners = get_user_runner_up_probs(user_db, num_sims, limit=3)
    user_thirds = get_user_third_place_probs(user_db, num_sims, limit=3)

    base_champs = get_champion_probs(limit=48)
    base_runners = get_runner_up_probs(limit=3)
    base_thirds = get_third_place_probs(limit=3)

    base_champ_dict = dict(zip(base_champs["team"], base_champs["probability"]))
    base_runner_dict = dict(zip(base_runners["team"], base_runners["probability"]))
    base_third_dict = dict(zip(base_thirds["team"], base_thirds["probability"]))

    # Build podium data
    def _top_team(df, base_dict):
        if df.empty:
            return ("TBD", 0.0, 0.0, 0.0)
        row = df.iloc[0]
        bp = base_dict.get(row["team"], 0.0)
        return (row["team"], row["probability"], bp, row["probability"] - bp)

    champ = _top_team(user_champs, base_champ_dict)
    runner = _top_team(user_runners, base_runner_dict)
    third = _top_team(user_thirds, base_third_dict)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        render_podium_with_shifts("Champion", champ[0], champ[1], champ[2],
                                  champ[3], "wc-podium-gold")
    with col2:
        render_podium_with_shifts("Runner-up", runner[0], runner[1], runner[2],
                                  runner[3], "wc-podium-silver")
    with col3:
        render_podium_with_shifts("3rd Place", third[0], third[1], third[2],
                                  third[3], "wc-podium-bronze")

    # Championship probability shifts table
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="wc-section-sub">Championship Probability Shifts</div>',
        unsafe_allow_html=True,
    )

    podium_data = []
    for _, row in user_champs.iterrows():
        team = row["team"]
        bp = base_champ_dict.get(team, 0.0)
        podium_data.append({
            "team": team,
            "user_prob": row["probability"],
            "base_prob": bp,
            "shift": row["probability"] - bp,
        })

    # Also include baseline teams not in user results
    user_team_set = set(user_champs["team"])
    for _, row in base_champs.iterrows():
        if row["team"] not in user_team_set:
            podium_data.append({
                "team": row["team"],
                "user_prob": 0.0,
                "base_prob": row["probability"],
                "shift": -row["probability"],
            })

    podium_data.sort(key=lambda d: d["shift"], reverse=True)
    render_champion_shifts_table(podium_data[:15])


def _render_groups_view(user_db, num_sims):
    """Group finishing orders with position shift indicators."""

    render_info_box(
        "Most likely finishing order per group from your simulation. "
        "The <strong>Shift</strong> column shows how each team's position "
        "moved compared to the baseline."
    )

    # Baseline group orders
    baseline_groups = get_all_groups_most_likely()
    baseline_orders = {}
    for _, row in baseline_groups.iterrows():
        baseline_orders[row["group_name"]] = row["team_order"].split(",")

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
                    render_sim_group_table(standings, base_order, group_name)


def _render_teams_view(user_db, num_sims):
    """Per-team progression view sorted by biggest positive shift."""

    render_info_box(
        "Each team's stage-by-stage probabilities from your simulation compared "
        "to the baseline. Teams are sorted by their overall tournament depth, known "
        "as their <strong>Average Stage Score</strong>. This score calculates "
        "expected progression by calculating the weighted average of the stages they reached "
        "(e.g., Group Stage = 0, R32 = 1 ... Winner = 6). <br><br>"
        "<strong>A higher average score indicates a deeper expected run.</strong>"
    )

    # Average stage score for user and baseline
    user_finish = get_user_all_team_best_finish(user_db, num_sims)
    baseline_finish = get_baseline_all_team_best_finish()
    
    # Create baseline dicts for O(1) lookups
    base_champ_dict = dict(zip(baseline_finish["team"], baseline_finish["champ_prob"]))
    base_score_dict = dict(zip(baseline_finish["team"], baseline_finish["avg_stage_score"]))

    # Build shift list
    team_list = []
    for _, row in user_finish.iterrows():
        team = row["team"]
        user_champ = row["champ_prob"]
        base_champ = base_champ_dict.get(team, 0.0)
        user_score = row["avg_stage_score"]
        base_score = base_score_dict.get(team, 0.0)
        
        team_list.append({
            "team": team,
            "user_champ": user_champ,
            "base_champ": base_champ,
            "champ_shift": user_champ - base_champ,
            "avg_score": user_score,
            "avg_score_shift": user_score - base_score,
        })

    team_list.sort(key=lambda d: d["avg_score"], reverse=True)

    # Count auto-expanded teams and show explanation
    auto_expanded = [t for t in team_list if t["champ_shift"] > 2.0]
    if auto_expanded:
        st.caption(
            f"Teams with a championship probability shift greater than +2% are "
            f"auto-expanded ({len(auto_expanded)} team{'s' if len(auto_expanded) != 1 else ''})."
        )

    # Compact table overview first
    html = '<div class="wc-card-flat" style="padding:0.75rem;">'
    html += '<table class="wc-sim-results-table"><thead><tr>'
    html += '<th>#</th><th>Team</th><th>Champion %</th><th>Baseline</th><th>Shift</th><th>Avg Score</th><th>Shift</th>'
    html += '</tr></thead><tbody>'

    for rank, t in enumerate(team_list[:15], 1):
        flag = get_flag(t["team"])
        champ_shift_badge = render_shift_badge(t["champ_shift"])
        score_shift_badge = render_score_shift_badge(t["avg_score_shift"])
        
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
        '<div class="wc-section-sub">Stage-by-Stage Breakdown</div>',
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
            render_team_progression_table(team, user_stages, baseline_stages)


# ── Page layout ──────────────────────────────────────────────────────────────


_init_state()

st.markdown(
    '<div class="wc-section-header">Simulator</div>',
    unsafe_allow_html=True,
)

render_info_box(
    "Adjust team FIFA rankings and run your own simulations to see how "
    "probabilities shift compared to the 100,000-simulation baseline. "
    "Change any team's rank, hit <strong>Run Simulation</strong>, and "
    "explore the results."
)

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
    _cascade_rank(t_name, new_r)
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

        st.slider(
            "FIFA Rank",
            min_value=1,
            max_value=100,
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
        disabled=not _has_rank_changes(),
    ):
        _run_simulation()
        st.rerun()

with col_reset:
    if st.button("Reset All Ranks", use_container_width=True):
        st.session_state["sim_adjusted_ranks"] = dict(defaults)
        st.session_state["sim_expanded_team"] = None
        st.session_state["sim_has_results"] = False
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
        options=["Podium", "Groups", "Teams"],
        default="Podium",
    )

    user_db = st.session_state["sim_user_db"]

    if results_view == "Podium":
        _render_podium_view(user_db, SIMULATOR_NUM_SIMS)
    elif results_view == "Groups":
        _render_groups_view(user_db, SIMULATOR_NUM_SIMS)
    elif results_view == "Teams":
        _render_teams_view(user_db, SIMULATOR_NUM_SIMS)
