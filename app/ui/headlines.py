"""
Headline generation for the Simulator page.

Produces a ranked list of Headline objects from simulation results,
covering three narrative categories:

1. Champion Flips   — changes in the top-5 championship favorites
2. Group Upsets     — groups whose most likely finishing order changed
3. Team Depth Shifts — biggest statistically significant tournament depth moves
"""

from dataclasses import dataclass, field
import math

import duckdb
import pandas as pd

from ui.flags import get_flag
from db.simulator_queries import (
    get_user_champion_probs,
    get_user_all_team_best_finish,
    get_user_stage_reach_probs,
    get_user_group_standings,
)
from db.landing_queries import (
    get_champion_probs,
    get_baseline_all_team_best_finish,
)
from db.team_queries import get_team_stage_reach_probs
from db.competition_queries import get_all_groups_most_likely
from config import GROUP_NAMES


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class Headline:
    """A single headline to display in the simulator."""
    emoji: str              # e.g. "🏆", "⚔️", "📈"
    label: str              # e.g. "NEW CONTENDER", "GROUP UPSET"
    html: str               # Description HTML (may contain spans/flags)
    priority: float         # Higher = shown first (magnitude of effect)
    teams: list = field(default_factory=list)  # Teams involved (for dedup)
    category: str = ""      # "champion", "group", "depth"


# ── Stat-sig helpers ─────────────────────────────────────────────────────────

def _is_stat_sig_prop(user_prob: float, base_prob: float, num_sims: int) -> bool:
    """Z-test for difference in proportions (percentages 0-100)."""
    p_hat = user_prob / 100.0
    p_0 = base_prob / 100.0
    if p_0 == 0 or p_0 == 1:
        return p_hat != p_0
    se = math.sqrt((p_0 * (1 - p_0)) / num_sims)
    if se == 0:
        return False
    z = (p_hat - p_0) / se
    return abs(z) > 1.96


def _is_stat_sig_mean(user_mean, base_mean, user_sd, num_sims) -> bool:
    """Z-test for difference in means."""
    if pd.isna(user_sd) or user_sd == 0 or num_sims == 0:
        return user_mean != base_mean
    t = (user_mean - base_mean) / (user_sd / math.sqrt(num_sims))
    return abs(t) > 1.96


# ── Headline generators ─────────────────────────────────────────────────────

def _champion_flip_headlines(
    user_db: duckdb.DuckDBPyConnection,
    num_sims: int,
) -> list[Headline]:
    """Detect changes in the top-5 championship favorites."""
    headlines: list[Headline] = []

    user_champs = get_user_champion_probs(user_db, num_sims, limit=48)
    base_champs = get_champion_probs(limit=48)

    user_dict = dict(zip(user_champs["team"], user_champs["probability"]))
    base_dict = dict(zip(base_champs["team"], base_champs["probability"]))

    # Sorted top-5 lists
    base_top5 = list(base_champs.head(5)["team"])
    user_top5 = list(user_champs.head(5)["team"])

    base_leader = base_top5[0] if base_top5 else None
    user_leader = user_top5[0] if user_top5 else None

    # 1. Leader change — the most dramatic headline
    if base_leader and user_leader and base_leader != user_leader:
        old_prob = base_dict.get(base_leader, 0)
        new_prob = user_dict.get(user_leader, 0)
        # Only surface if both teams' probability shifts are stat-sig
        old_base_prob = base_dict.get(base_leader, 0)
        new_base_prob = base_dict.get(user_leader, 0)
        if _is_stat_sig_prop(user_dict.get(user_leader, 0), new_base_prob, num_sims) and \
           _is_stat_sig_prop(user_dict.get(base_leader, 0), old_base_prob, num_sims):
            old_flag = get_flag(base_leader)
            new_flag = get_flag(user_leader)
            headlines.append(Headline(
                emoji="👑",
                label="DETHRONED",
                html=(
                    f"{old_flag} <strong>{base_leader}</strong> is no longer the tournament "
                    f"favorite. {new_flag} <strong>{user_leader}</strong> now leads at "
                    f"<span class='wc-shift-positive'>{new_prob:.1f}%</span>."
                ),
                priority=20 + new_prob,
                teams=[base_leader, user_leader],
                category="champion",
            ))

    # 2. New entrants to the top-5
    for team in user_top5:
        if team not in base_top5 and team != user_leader:
            user_prob = user_dict.get(team, 0)
            base_prob = base_dict.get(team, 0)
            if _is_stat_sig_prop(user_prob, base_prob, num_sims):
                flag = get_flag(team)
                headlines.append(Headline(
                    emoji="🏆",
                    label="NEW CONTENDER",
                    html=(
                        f"{flag} <strong>{team}</strong> has entered the top-5 "
                        f"championship favorites "
                        f"(<span class='wc-shift-positive'>"
                        f"{base_prob:.1f}% → {user_prob:.1f}%</span>)."
                    ),
                    priority=15 + abs(user_prob - base_prob),
                    teams=[team],
                    category="champion",
                ))

    # 3. Teams dropped out of top-5
    for team in base_top5:
        if team not in user_top5 and not any(team in h.teams for h in headlines):
            user_prob = user_dict.get(team, 0)
            base_prob = base_dict.get(team, 0)
            if _is_stat_sig_prop(user_prob, base_prob, num_sims):
                flag = get_flag(team)
                headlines.append(Headline(
                    emoji="📉",
                    label="FALLEN FAVORITE",
                    html=(
                        f"{flag} <strong>{team}</strong> has dropped out of the top-5 "
                        f"favorites "
                        f"(<span class='wc-shift-negative'>"
                        f"{base_prob:.1f}% → {user_prob:.1f}%</span>)."
                    ),
                    priority=14 + abs(base_prob - user_prob),
                    teams=[team],
                    category="champion",
                ))

    return headlines


def _group_upset_headlines(
    user_db: duckdb.DuckDBPyConnection,
    num_sims: int,
) -> list[Headline]:
    """Detect groups whose most likely finishing order changed.

    Only surfaces a headline when the rising team also has a
    statistically significant shift in tournament depth, preventing
    modal group-order noise from appearing as a headline.
    """
    headlines: list[Headline] = []

    baseline_groups = get_all_groups_most_likely()
    baseline_orders: dict[str, list[str]] = {}
    for _, row in baseline_groups.iterrows():
        baseline_orders[row["group_name"]] = row["team_order"].split(",")

    # Build a set of teams with stat-sig depth shifts for gating
    user_finish = get_user_all_team_best_finish(user_db, num_sims)
    baseline_finish = get_baseline_all_team_best_finish()
    base_score_dict = dict(zip(baseline_finish["team"], baseline_finish["avg_stage_score"]))

    sig_depth_teams: set[str] = set()
    for _, row in user_finish.iterrows():
        team = row["team"]
        user_sc = row["avg_stage_score"]
        user_sd = row["stddev_stage_score"]
        base_sc = base_score_dict.get(team, 0.0)
        if _is_stat_sig_mean(user_sc, base_sc, user_sd, num_sims):
            sig_depth_teams.add(team)

    for group_name in GROUP_NAMES:
        user_standings = get_user_group_standings(user_db, num_sims, group_name)
        if not user_standings:
            continue
        base_order = baseline_orders.get(group_name, [])
        user_order = [r["team"] for r in user_standings]

        if user_order == base_order:
            continue

        # Find the most dramatic positional change
        base_positions = {team: i for i, team in enumerate(base_order)}
        biggest_rise_team = None
        biggest_rise = 0

        for new_pos, team in enumerate(user_order):
            old_pos = base_positions.get(team, new_pos)
            rise = old_pos - new_pos  # positive = moved up
            if rise > biggest_rise:
                biggest_rise = rise
                biggest_rise_team = team

        # Only surface if the rising team has a stat-sig depth shift
        if biggest_rise_team and biggest_rise > 0 and biggest_rise_team in sig_depth_teams:
            flag = get_flag(biggest_rise_team)
            old_pos = base_positions.get(biggest_rise_team, 0) + 1
            new_pos = user_order.index(biggest_rise_team) + 1

            ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
            old_str = ordinals.get(old_pos, f"{old_pos}th")
            new_str = ordinals.get(new_pos, f"{new_pos}th")

            headlines.append(Headline(
                emoji="⚔️",
                label=f"GROUP {group_name} UPSET",
                html=(
                    f"Group {group_name} has a new most-likely order — "
                    f"{flag} <strong>{biggest_rise_team}</strong> rises from "
                    f"{old_str} to {new_str}."
                ),
                priority=10 + biggest_rise * 3,
                teams=[biggest_rise_team],
                category="group",
            ))

    return headlines


def _depth_shift_headlines(
    user_db: duckdb.DuckDBPyConnection,
    num_sims: int,
    overrides: dict,
) -> list[Headline]:
    """Detect biggest statistically significant tournament depth shifts.

    This is the existing Rising Stock / Butterfly Effect / Slipping Standards logic,
    but extracted and returning Headline objects.
    """
    headlines: list[Headline] = []

    user_finish = get_user_all_team_best_finish(user_db, num_sims)
    baseline_finish = get_baseline_all_team_best_finish()
    base_score_dict = dict(zip(baseline_finish["team"], baseline_finish["avg_stage_score"]))

    # Find teams with statistically significant shifts
    sig_teams = []
    for _, row in user_finish.iterrows():
        team = row["team"]
        user_sc = row["avg_stage_score"]
        user_sd = row["stddev_stage_score"]
        base_sc = base_score_dict.get(team, 0.0)

        if _is_stat_sig_mean(user_sc, base_sc, user_sd, num_sims):
            sig_teams.append({
                "team": team,
                "shift": user_sc - base_sc,
                "user_score": user_sc,
                "base_score": base_sc,
            })

    sig_teams.sort(key=lambda t: abs(t["shift"]), reverse=True)

    for t_data in sig_teams[:6]:
        team = t_data["team"]
        shift = t_data["shift"]
        flag = get_flag(team)

        # Find the stage with the largest significant shift
        user_stages = get_user_stage_reach_probs(user_db, num_sims, team)
        base_stages = get_team_stage_reach_probs(team)

        max_sig_stage = None
        max_sig_stage_shift = 0.0

        baseline_dict = dict(zip(base_stages["stage"], base_stages["probability"]))
        for _, u_row in user_stages.iterrows():
            stg = u_row["stage"]
            if stg == "GROUP_STAGE":
                continue
            u_prob = u_row["probability"]
            b_prob = baseline_dict.get(stg, 0.0)

            if _is_stat_sig_prop(u_prob, b_prob, num_sims):
                stg_shift = u_prob - b_prob
                if (shift > 0 and stg_shift > max_sig_stage_shift) or \
                   (shift < 0 and stg_shift < max_sig_stage_shift):
                    max_sig_stage_shift = stg_shift
                    max_sig_stage = u_row["display_name"]

        if shift > 0:
            emoji = "📈" if team in overrides else "🦋"
            label = "RISING STOCK" if team in overrides else "BUTTERFLY EFFECT"
            if max_sig_stage:
                desc = (
                    f"{flag} <strong>{team}</strong> has improved their chances to "
                    f"reach the {max_sig_stage} by "
                    f"<span class='wc-shift-positive'>+{max_sig_stage_shift:.1f}%</span>."
                )
            else:
                desc = (
                    f"{flag} <strong>{team}</strong> has improved their expected "
                    f"Tournament Depth (+{shift:.2f})."
                )
        else:
            emoji = "⚠️" if team in overrides else "🦋"
            label = "SLIPPING STANDARDS" if team in overrides else "BUTTERFLY EFFECT"
            if max_sig_stage:
                desc = (
                    f"{flag} <strong>{team}</strong> has suffered a significant drop "
                    f"in chances to reach the {max_sig_stage} "
                    f"(<span class='wc-shift-negative'>{max_sig_stage_shift:.1f}%</span>)."
                )
            else:
                desc = (
                    f"{flag} <strong>{team}</strong> has worsened their expected "
                    f"Tournament Depth ({shift:.2f})."
                )

        headlines.append(Headline(
            emoji=emoji,
            label=label,
            html=desc,
            priority=abs(shift) * 5,
            teams=[team],
            category="depth",
        ))

    return headlines


# ── Main entry point ─────────────────────────────────────────────────────────

def generate_headlines(
    user_db: duckdb.DuckDBPyConnection,
    num_sims: int,
    overrides: dict,
    max_headlines: int = 6,
) -> list[Headline]:
    """Generate a diverse, ranked list of headlines.

    Collects headlines from all three generators, deduplicates by team,
    and returns up to `max_headlines` items sorted by priority.

    Args:
        user_db: DuckDB connection with user simulation results.
        num_sims: Number of simulations run.
        overrides: Dict of user rank overrides (team -> rank).
        max_headlines: Maximum number of headlines to return.

    Returns:
        List of Headline objects, sorted by priority (highest first).
    """
    # Collect from all generators (champion flips first for highest priority)
    all_headlines: list[Headline] = []
    all_headlines.extend(_champion_flip_headlines(user_db, num_sims))
    all_headlines.extend(_group_upset_headlines(user_db, num_sims))
    all_headlines.extend(_depth_shift_headlines(user_db, num_sims, overrides))

    # Sort by priority (highest first)
    all_headlines.sort(key=lambda h: h.priority, reverse=True)

    # Deduplicate: don't show the same team in multiple headlines
    seen_teams: set[str] = set()
    result: list[Headline] = []
    # Track category counts for diversity
    category_counts: dict[str, int] = {"champion": 0, "group": 0, "depth": 0}
    max_per_category = max(2, max_headlines // 2)

    for h in all_headlines:
        if len(result) >= max_headlines:
            break
        # Skip if any of this headline's teams already appeared
        if any(t in seen_teams for t in h.teams):
            continue
        # Cap per category for diversity
        if category_counts.get(h.category, 0) >= max_per_category:
            continue
        result.append(h)
        seen_teams.update(h.teams)
        category_counts[h.category] = category_counts.get(h.category, 0) + 1

    return result
