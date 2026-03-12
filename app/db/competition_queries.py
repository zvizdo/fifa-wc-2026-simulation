"""
Database queries for the Competition Explorer page.
"""
import pandas as pd
import streamlit as st
from db.connection import get_db
from db.connection import get_total_sims


@st.cache_data
def get_knockout_bracket_overview() -> pd.DataFrame:
    """Most likely winner for each knockout match (73-104).

    Returns DataFrame with columns: match_number, stage, city, most_likely_winner, prob
    """
    con = get_db()
    return con.execute(f"""
        WITH match_winners AS (
            SELECT match_number, stage, city, winner, COUNT(*) AS cnt
            FROM matches
            WHERE match_number >= 73
            GROUP BY match_number, stage, city, winner
        ),
        ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY match_number ORDER BY cnt DESC) AS rn,
                SUM(cnt) OVER (PARTITION BY match_number) AS total
            FROM match_winners
        )
        SELECT match_number, stage, city,
               winner AS most_likely_winner,
               ROUND(cnt * 100.0 / total, 1) AS prob
        FROM ranked
        WHERE rn = 1
        ORDER BY match_number
    """).fetchdf()


@st.cache_data
def get_stage_matchups(stage: str, limit: int = 5) -> pd.DataFrame:
    """Top N most likely matchups for a knockout stage.

    Normalizes team order alphabetically to avoid double-counting.
    Returns DataFrame with columns: team1, team2, count, probability
    """
    con = get_db()
    return con.execute(f"""
        SELECT
            CASE WHEN home_team < away_team THEN home_team ELSE away_team END AS team1,
            CASE WHEN home_team < away_team THEN away_team ELSE home_team END AS team2,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability
        FROM matches
        WHERE stage = ?
        GROUP BY team1, team2
        ORDER BY count DESC
        LIMIT ?
    """, [stage, limit]).fetchdf()


@st.cache_data
def get_final_matchups(limit: int = 5) -> pd.DataFrame:
    """Top N most likely Final matchups.

    Returns DataFrame with columns: team1, team2, count, probability
    """
    return get_stage_matchups("FINAL", limit)


@st.cache_data
def get_matchup_results(stage: str, team1: str, team2: str, limit: int = 8) -> pd.DataFrame:
    """Score distribution for a specific matchup at a given stage.

    Returns DataFrame with columns: home_team, away_team, home_score, away_score, winner, count, probability
    """
    con = get_db()
    # Count how many times this matchup occurred
    matchup_total = con.execute("""
        SELECT COUNT(*) FROM matches
        WHERE stage = ? AND (
            (home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?)
        )
    """, [stage, team1, team2, team2, team1]).fetchone()[0]

    if matchup_total == 0:
        return pd.DataFrame(columns=["home_team", "away_team", "home_score", "away_score", "winner", "count", "probability"])

    return con.execute(f"""
        WITH normalized AS (
            SELECT
                CASE WHEN home_team = ? THEN home_score ELSE away_score END AS home_score,
                CASE WHEN home_team = ? THEN away_score ELSE home_score END AS away_score,
                winner
            FROM matches
            WHERE stage = ? AND (
                (home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?)
            )
        )
        SELECT
            ? AS home_team,
            ? AS away_team,
            home_score,
            away_score,
            winner,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / {matchup_total}, 2) AS probability
        FROM normalized
        GROUP BY home_score, away_score, winner
        ORDER BY count DESC
        LIMIT ?
    """, [team1, team1, stage, team1, team2, team2, team1, team1, team2, limit]).fetchdf()


@st.cache_data
def get_all_groups_most_likely() -> pd.DataFrame:
    """Most likely final standing for each group.

    Returns DataFrame with columns: group_name, team_order, count, probability
    where team_order is a comma-separated string of teams in position order.
    """
    con = get_db()
    return con.execute(f"""
        WITH group_outcomes AS (
            SELECT group_name, sim_id,
                STRING_AGG(team, ',' ORDER BY position) AS team_order
            FROM group_standings
            GROUP BY group_name, sim_id
        ),
        counted AS (
            SELECT group_name, team_order, COUNT(*) AS count,
                   ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability,
                   ROW_NUMBER() OVER (PARTITION BY group_name ORDER BY COUNT(*) DESC) AS rn
            FROM group_outcomes
            GROUP BY group_name, team_order
        )
        SELECT group_name, team_order, count, probability
        FROM counted
        WHERE rn = 1
        ORDER BY group_name
    """).fetchdf()


@st.cache_data
def get_group_most_likely_standings(group_name: str, team_order: str) -> list[dict]:
    """Most representative stats for a specific group ordering.

    Finds all sims that produced the given team_order for the group. Instead of independent
    MODE calculations (which can lead to mathematically impossible combinations like 9, 6, 3, 1 points),
    it identifies the most frequent points distribution, then the most frequent goal difference
    distribution within that, and returns the exact valid standings from a single representative simulation.

    Returns list of row dicts with keys: position, team, played, wins, draws,
    losses, goal_difference, points, advanced.
    """
    con = get_db()
    standings = con.execute("""
        WITH matching_sims AS (
            SELECT sim_id
            FROM group_standings
            WHERE group_name = ?
            GROUP BY sim_id
            HAVING STRING_AGG(team, ',' ORDER BY position) = ?
        ),
        sims_data AS (
            SELECT sim_id,
                   STRING_AGG(points::VARCHAR, ',' ORDER BY position) as pts_dist,
                   STRING_AGG(goal_difference::VARCHAR, ',' ORDER BY position) as gd_dist
            FROM group_standings
            WHERE group_name = ? AND sim_id IN (SELECT sim_id FROM matching_sims)
            GROUP BY sim_id
        ),
        ranked_sims AS (
            SELECT sim_id,
                   COUNT(*) OVER (PARTITION BY pts_dist) as pt_freq,
                   COUNT(*) OVER (PARTITION BY pts_dist, gd_dist) as pt_gd_freq
            FROM sims_data
        )
        SELECT
            position, team, played, wins, draws, losses,
            goal_difference, points, advanced
        FROM group_standings
        WHERE group_name = ?
          AND sim_id = (
              SELECT sim_id FROM ranked_sims
              ORDER BY pt_freq DESC, pt_gd_freq DESC, sim_id
              LIMIT 1
          )
        ORDER BY position
    """, [group_name, team_order, group_name, group_name]).fetchdf()
    return standings.to_dict("records")


@st.cache_data
def get_group_scenarios(group_name: str, limit: int = 5) -> list[dict]:
    """Top N most likely group outcomes for a specific group.

    Returns list of dicts, each with keys: team_order, probability, standings
    where standings is a list of row dicts with MODE-based stats.
    """
    con = get_db()
    # Get top N team orderings
    top_orderings = con.execute(f"""
        WITH group_outcomes AS (
            SELECT sim_id,
                STRING_AGG(team, ',' ORDER BY position) AS team_order
            FROM group_standings
            WHERE group_name = ?
            GROUP BY sim_id
        )
        SELECT team_order, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability
        FROM group_outcomes
        GROUP BY team_order
        ORDER BY count DESC
        LIMIT ?
    """, [group_name, limit]).fetchdf()

    scenarios = []
    for _, row in top_orderings.iterrows():
        standings = get_group_most_likely_standings(group_name, row["team_order"])
        if not standings:
            continue
        scenarios.append({
            "team_order": row["team_order"],
            "probability": row["probability"],
            "standings": standings,
        })

    return scenarios


@st.cache_data
def get_third_place_advancement() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Which teams and groups most often advance via the best 3rd-place route.

    Returns a tuple of two DataFrames:
    - teams_df: columns team, group_name, adv_pct, avg_points, avg_gd
      (ordered by adv_pct DESC, only teams that advanced at least once)
    - groups_df: columns group_name, adv_pct
      (ordered by adv_pct DESC)
    """
    con = get_db()
    teams_df = con.execute(f"""
        SELECT team,
               MODE(group_name) AS group_name,
               ROUND(SUM(CASE WHEN advanced THEN 1 ELSE 0 END) * 100.0 / {get_total_sims()}, 1) AS adv_pct,
               ROUND(AVG(points), 1) AS avg_points,
               ROUND(AVG(goal_difference), 1) AS avg_gd
        FROM third_place_ranks
        GROUP BY team
        HAVING SUM(CASE WHEN advanced THEN 1 ELSE 0 END) > 0
        ORDER BY adv_pct DESC
    """).fetchdf()

    groups_df = con.execute(f"""
        SELECT group_name,
               ROUND(SUM(CASE WHEN advanced THEN 1 ELSE 0 END) * 100.0 / {get_total_sims()}, 1) AS adv_pct
        FROM group_standings
        WHERE position = 3
        GROUP BY group_name
        ORDER BY adv_pct DESC
    """).fetchdf()

    return teams_df, groups_df


@st.cache_data
def get_stage_winner_probs(stage: str, match_number: int | None = None) -> pd.DataFrame:
    """Probability distribution of winners for a specific stage (or match number).

    Returns DataFrame with columns: team, count, probability
    """
    con = get_db()
    if match_number is not None:
        return con.execute(f"""
            SELECT winner AS team, COUNT(*) AS count,
                   ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability
            FROM matches
            WHERE match_number = ?
            GROUP BY winner
            ORDER BY count DESC
        """, [match_number]).fetchdf()

    return con.execute(f"""
        SELECT winner AS team, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability
        FROM matches
        WHERE stage = ?
        GROUP BY winner
        ORDER BY count DESC
    """, [stage]).fetchdf()


@st.cache_data
def get_head_to_head(team1: str, team2: str) -> dict | None:
    """Head-to-head stats for two teams across all knockout stages.

    Returns dict with keys:
    - meeting_count: total matches between the two teams
    - meeting_pct: percentage of sims where they meet
    - stage_distribution: list of {stage, stage_label, count, abs_pct, rel_pct}
    - win_pcts: {team1_name, team1_pct, team2_name, team2_pct}
    Returns None if teams never met.
    """
    from config import STAGE_DISPLAY_NAMES, STAGE_ORDER

    con = get_db()
    raw = con.execute("""
        SELECT stage, winner, COUNT(*) AS cnt
        FROM matches
        WHERE stage != 'GROUP_STAGE'
          AND ((home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?))
        GROUP BY stage, winner
    """, [team1, team2, team2, team1]).fetchdf()

    if raw.empty:
        return None

    meeting_count = int(raw["cnt"].sum())
    meeting_pct = round(meeting_count * 100.0 / get_total_sims(), 2)

    # Stage distribution
    stage_counts = raw.groupby("stage")["cnt"].sum()
    stage_order = [s for s in STAGE_ORDER if s in stage_counts.index]
    stage_distribution = []
    for stage in stage_order:
        cnt = int(stage_counts[stage])
        stage_distribution.append({
            "stage": stage,
            "stage_label": STAGE_DISPLAY_NAMES.get(stage, stage),
            "count": cnt,
            "abs_pct": round(cnt * 100.0 / get_total_sims(), 2),
            "rel_pct": round(cnt * 100.0 / meeting_count, 1),
        })
    stage_distribution.sort(key=lambda x: x["abs_pct"], reverse=True)

    # Win percentages
    win_counts = raw.groupby("winner")["cnt"].sum()
    t1_wins = int(win_counts.get(team1, 0))
    t2_wins = int(win_counts.get(team2, 0))
    win_pcts = {
        "team1_name": team1,
        "team1_pct": round(t1_wins * 100.0 / meeting_count, 1),
        "team2_name": team2,
        "team2_pct": round(t2_wins * 100.0 / meeting_count, 1),
    }

    return {
        "meeting_count": meeting_count,
        "meeting_pct": meeting_pct,
        "stage_distribution": stage_distribution,
        "win_pcts": win_pcts,
    }


@st.cache_data
def get_group_position_probabilities(group_name: str) -> pd.DataFrame:
    """
    Get probability of each team finishing in position 1, 2, 3, 4.
    Returns DataFrame:
        - Index: team name
        - Columns: 1, 2, 3, 4 (probabilities in %)
        - Sorted by likely finish order (average position).
    """
    con = get_db()
    
    # 1. Get average position for sorting
    avg_pos = con.execute("""
        SELECT team, AVG(position) as avg_pos
        FROM group_standings
        WHERE group_name = ?
        GROUP BY team
    """, [group_name]).fetchdf().set_index("team")
    
    # 2. Get probabilities per position
    probs = con.execute(f"""
        SELECT team, position,
               ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 1) as prob
        FROM group_standings
        WHERE group_name = ?
        GROUP BY team, position
    """, [group_name]).fetchdf()
    
    if probs.empty:
        return pd.DataFrame()

    # Pivot: Index=team, Columns=position, Values=prob
    pivot = probs.pivot(index="team", columns="position", values="prob").fillna(0.0)
    
    # Join with avg_pos for sorting
    # Note: We need to ensure columns 1,2,3,4 exist even if 0 probability (though unlikely in group stage)
    for i in range(1, 5):
        if i not in pivot.columns:
            pivot[i] = 0.0
            
    result = pivot.join(avg_pos).sort_values("avg_pos")
    
    return result.drop(columns=["avg_pos"])
