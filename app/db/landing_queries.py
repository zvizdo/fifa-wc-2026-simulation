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
