"""
Database queries for the Team Explorer page.
"""
import pandas as pd
import streamlit as st
from db.connection import get_db
from db.connection import get_total_sims


@st.cache_data
def get_all_teams() -> pd.DataFrame:
    """Get all 48 teams with group, FIFA rank, confederation.

    Returns DataFrame with columns: team, group_name, fifa_rank, confederation
    """
    con = get_db()
    return con.execute("""
        SELECT DISTINCT team, group_name, fifa_rank, confederation
        FROM group_standings
        WHERE sim_id = (SELECT MIN(sim_id) FROM group_standings)
        ORDER BY group_name, fifa_rank
    """).fetchdf()


@st.cache_data
def get_team_outcome_distribution(team: str) -> pd.DataFrame:
    """Probability of each tournament outcome for a team.

    Uses a single-pass aggregation for performance.
    Returns DataFrame with columns: outcome, count, probability
    """
    con = get_db()
    return con.execute(f"""
        WITH team_in_group AS (
            SELECT sim_id FROM group_standings WHERE team = ?
        ),
        team_matches AS (
            SELECT m.sim_id, m.match_number, m.stage,
                   CASE WHEN m.winner = ? THEN 1 ELSE 0 END AS won
            FROM matches m
            INNER JOIN team_in_group tig ON m.sim_id = tig.sim_id
            WHERE m.home_team = ? OR m.away_team = ?
        ),
        team_agg AS (
            SELECT sim_id,
                MAX(CASE WHEN match_number = 104 AND won = 1 THEN 1 ELSE 0 END) AS is_champion,
                MAX(CASE WHEN match_number = 104 AND won = 0 THEN 1 ELSE 0 END) AS is_runner_up,
                MAX(CASE WHEN match_number = 103 AND won = 1 THEN 1 ELSE 0 END) AS is_third,
                MAX(CASE WHEN match_number = 103 AND won = 0 THEN 1 ELSE 0 END) AS is_fourth,
                MAX(CASE WHEN stage = 'QUARTER_FINALS' THEN 1 ELSE 0 END) AS reached_qf,
                MAX(CASE WHEN stage = 'ROUND_OF_16' THEN 1 ELSE 0 END) AS reached_r16,
                MAX(CASE WHEN stage = 'ROUND_OF_32' THEN 1 ELSE 0 END) AS reached_r32,
                MAX(CASE WHEN stage = 'SEMI_FINALS' THEN 1 ELSE 0 END) AS reached_sf
            FROM team_matches
            GROUP BY sim_id
        ),
        team_outcomes AS (
            SELECT sim_id,
                CASE
                    WHEN is_champion = 1 THEN 'Champion'
                    WHEN is_runner_up = 1 THEN 'Runner-up'
                    WHEN is_third = 1 THEN '3rd Place'
                    WHEN is_fourth = 1 THEN '4th Place'
                    WHEN reached_sf = 1 AND is_third = 0 AND is_fourth = 0 THEN 'Semi-Finals Exit'
                    WHEN reached_qf = 1 AND reached_sf = 0 THEN 'Quarter-Finals Exit'
                    WHEN reached_r16 = 1 AND reached_qf = 0 THEN 'Round of 16 Exit'
                    WHEN reached_r32 = 1 AND reached_r16 = 0 THEN 'Round of 32 Exit'
                    ELSE 'Group Stage Exit'
                END AS outcome
            FROM team_agg
        ),
        all_sims AS (
            SELECT sim_id, 'Group Stage Exit' AS outcome
            FROM team_in_group
            WHERE sim_id NOT IN (SELECT sim_id FROM team_agg)
            UNION ALL
            SELECT sim_id, outcome FROM team_outcomes
        )
        SELECT outcome, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability
        FROM all_sims
        GROUP BY outcome
        ORDER BY count DESC
    """, [team, team, team, team]).fetchdf()


@st.cache_data
def get_team_stage_reach_probs(team: str) -> pd.DataFrame:
    """Probability of reaching each tournament stage.

    Returns DataFrame with columns: stage, display_name, probability
    Includes Group Stage (always 100%) through Champion.
    """
    con = get_db()
    # Get group position probabilities
    group_adv = con.execute(f"""
        SELECT SUM(CASE WHEN advanced THEN 1 ELSE 0 END) * 100.0 / {get_total_sims()} AS adv_pct
        FROM group_standings WHERE team = ?
    """, [team]).fetchone()[0]

    # Appearance in each knockout stage
    knockout_probs = con.execute(f"""
        SELECT stage, COUNT(DISTINCT sim_id) AS appearances,
               ROUND(COUNT(DISTINCT sim_id) * 100.0 / {get_total_sims()}, 2) AS probability
        FROM matches
        WHERE (home_team = ? OR away_team = ?) AND stage != 'GROUP_STAGE'
        GROUP BY stage
    """, [team, team]).fetchdf()

    # Also get champion probability
    champion = con.execute(f"""
        SELECT COUNT(*) AS cnt FROM matches
        WHERE match_number = 104 AND winner = ?
    """, [team]).fetchone()[0]
    champion_pct = round(champion * 100.0 / get_total_sims(), 2)

    stage_map = {
        "ROUND_OF_32": "Round of 32",
        "ROUND_OF_16": "Round of 16",
        "QUARTER_FINALS": "Quarter-Finals",
        "SEMI_FINALS": "Semi-Finals",
        "THIRD_PLACE": "3rd Place Match",
        "FINAL": "Final",
    }

    rows = [{"stage": "GROUP_STAGE", "display_name": "Group Stage", "probability": 100.0}]

    for stage_key, display in stage_map.items():
        match = knockout_probs[knockout_probs["stage"] == stage_key]
        prob = float(match["probability"].iloc[0]) if not match.empty else 0.0
        # For SF: combine SF + 3rd place match + final to get "reached SF"
        rows.append({"stage": stage_key, "display_name": display, "probability": prob})

    rows.append({"stage": "CHAMPION", "display_name": "Champion", "probability": champion_pct})

    return pd.DataFrame(rows)


@st.cache_data
def get_team_group_position_probs(team: str) -> pd.DataFrame:
    """Probability of finishing at each group position.

    Returns DataFrame with columns: position, count, probability
    """
    con = get_db()
    return con.execute(f"""
        SELECT position, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability
        FROM group_standings
        WHERE team = ?
        GROUP BY position
        ORDER BY position
    """, [team]).fetchdf()


@st.cache_data
def get_team_opponents(team: str, stage: str, limit: int = 8) -> pd.DataFrame:
    """Top opponents for a team at a given knockout stage.

    Returns DataFrame with columns: opponent, total, wins, losses, matchup_pct, win_rate
    """
    con = get_db()
    # Total times team appears in this stage
    total_appearances = con.execute("""
        SELECT COUNT(*) FROM matches
        WHERE stage = ? AND (home_team = ? OR away_team = ?)
    """, [stage, team, team]).fetchone()[0]

    if total_appearances == 0:
        return pd.DataFrame(columns=["opponent", "total", "wins", "losses", "matchup_pct", "win_rate"])

    return con.execute(f"""
        SELECT
            CASE WHEN home_team = ? THEN away_team ELSE home_team END AS opponent,
            COUNT(*) AS total,
            SUM(CASE WHEN winner = ? THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN winner != ? THEN 1 ELSE 0 END) AS losses,
            ROUND(COUNT(*) * 100.0 / {total_appearances}, 1) AS matchup_pct,
            ROUND(SUM(CASE WHEN winner = ? THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS win_rate
        FROM matches
        WHERE stage = ? AND (home_team = ? OR away_team = ?)
        GROUP BY opponent
        ORDER BY total DESC
        LIMIT ?
    """, [team, team, team, team, stage, team, team, limit]).fetchdf()


@st.cache_data
def get_team_info(team: str) -> dict:
    """Get team metadata (group, rank, confederation)."""
    con = get_db()
    row = con.execute("""
        SELECT team, group_name, fifa_rank, confederation
        FROM group_standings
        WHERE team = ? AND sim_id = (SELECT MIN(sim_id) FROM group_standings)
        LIMIT 1
    """, [team]).fetchdf()
    if row.empty:
        return {"team": team, "group_name": "?", "fifa_rank": 0, "confederation": "?"}
    return row.iloc[0].to_dict()
