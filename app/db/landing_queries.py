"""
Database queries for the Landing page.
"""
import pandas as pd
import streamlit as st
from db.connection import get_db
from config import TOTAL_SIMS


@st.cache_data
def get_champion_probs(limit: int = 3) -> pd.DataFrame:
    """Top N most likely champions (winners of match 104 / the Final).

    Returns DataFrame with columns: team, count, probability
    """
    con = get_db()
    return con.execute(f"""
        SELECT winner AS team, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {TOTAL_SIMS}, 2) AS probability
        FROM matches
        WHERE match_number = 104
        GROUP BY winner
        ORDER BY count DESC
        LIMIT ?
    """, [limit]).fetchdf()


@st.cache_data
def get_runner_up_probs(limit: int = 3) -> pd.DataFrame:
    """Top N most likely runners-up (losers of the Final).

    Returns DataFrame with columns: team, count, probability
    """
    con = get_db()
    return con.execute(f"""
        SELECT
            CASE WHEN winner = home_team THEN away_team ELSE home_team END AS team,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / {TOTAL_SIMS}, 2) AS probability
        FROM matches
        WHERE match_number = 104
        GROUP BY team
        ORDER BY count DESC
        LIMIT ?
    """, [limit]).fetchdf()


@st.cache_data
def get_third_place_probs(limit: int = 3) -> pd.DataFrame:
    """Top N most likely 3rd-place finishers (winners of match 103).

    Returns DataFrame with columns: team, count, probability
    """
    con = get_db()
    return con.execute(f"""
        SELECT winner AS team, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {TOTAL_SIMS}, 2) AS probability
        FROM matches
        WHERE match_number = 103
        GROUP BY winner
        ORDER BY count DESC
        LIMIT ?
    """, [limit]).fetchdf()


@st.cache_data
def get_baseline_all_team_best_finish() -> pd.DataFrame:
    """Average tournament depth score and champion probability for all teams in the baseline.

    Stage scores: GROUP=0, R32=1, R16=2, QF=3, SF=4, FINAL=5, CHAMPION=6
    Returns DataFrame with columns: team, avg_stage_score, champ_prob
    """
    con = get_db()
    return con.execute(f"""
        WITH team_sims AS (
            SELECT DISTINCT team, sim_id
            FROM group_standings
        ),
        team_max_stage AS (
            SELECT team, sim_id, MAX(stage_score) AS max_score
            FROM (
                -- Teams that made it to knockout stages get points based on the match
                SELECT home_team AS team, sim_id,
                    CASE
                        WHEN stage = 'FINAL' THEN 5
                        WHEN stage IN ('SEMI_FINALS', 'THIRD_PLACE') THEN 4
                        WHEN stage = 'QUARTER_FINALS' THEN 3
                        WHEN stage = 'ROUND_OF_16' THEN 2
                        WHEN stage = 'ROUND_OF_32' THEN 1
                        ELSE 0
                    END AS stage_score
                FROM matches WHERE stage != 'GROUP_STAGE'
                
                UNION ALL
                
                SELECT away_team AS team, sim_id,
                    CASE
                        WHEN stage = 'FINAL' THEN 5
                        WHEN stage IN ('SEMI_FINALS', 'THIRD_PLACE') THEN 4
                        WHEN stage = 'QUARTER_FINALS' THEN 3
                        WHEN stage = 'ROUND_OF_16' THEN 2
                        WHEN stage = 'ROUND_OF_32' THEN 1
                        ELSE 0
                    END AS stage_score
                FROM matches WHERE stage != 'GROUP_STAGE'
                
                UNION ALL
                
                -- Champions get 6 points
                SELECT winner AS team, sim_id, 6 AS stage_score
                FROM matches WHERE match_number = 104
            ) unified_stages
            GROUP BY team, sim_id
        ),
        combined_scores AS (
            SELECT ts.team, ts.sim_id, COALESCE(tms.max_score, 0) AS stage_score
            FROM team_sims ts
            LEFT JOIN team_max_stage tms ON ts.team = tms.team AND ts.sim_id = tms.sim_id
        ),
        champs AS (
            SELECT winner AS team, COUNT(*) AS wins
            FROM matches WHERE match_number = 104
            GROUP BY winner
        )
        SELECT cs.team,
               ROUND(AVG(cs.stage_score), 3) AS avg_stage_score,
               COALESCE(ROUND(c.wins * 100.0 / {TOTAL_SIMS}, 2), 0) AS champ_prob
        FROM combined_scores cs
        LEFT JOIN champs c ON c.team = cs.team
        GROUP BY cs.team, c.wins
        ORDER BY avg_stage_score DESC
    """).fetchdf()
