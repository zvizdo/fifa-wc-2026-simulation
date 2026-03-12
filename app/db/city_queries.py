"""
Database queries for the City Explorer page.
"""
import pandas as pd
import streamlit as st
from db.connection import get_db
from db.connection import get_total_sims


@st.cache_data
def get_city_overview() -> pd.DataFrame:
    """Overview of all 16 host cities with match counts and stages hosted.

    Returns DataFrame with columns: city, stadium, country, total_matches,
                                     num_knockout_matches, stages, match_numbers_str
    """
    con = get_db()
    return con.execute("""
        WITH city_info AS (
            SELECT city, stadium, country, match_number, stage
            FROM matches
            WHERE sim_id = (SELECT MIN(sim_id) FROM matches)
        )
        SELECT city,
               MODE(stadium) AS stadium,
               MODE(country) AS country,
               COUNT(*) AS total_matches,
               SUM(CASE WHEN stage != 'GROUP_STAGE' THEN 1 ELSE 0 END) AS num_knockout_matches,
               STRING_AGG(DISTINCT stage, ', ' ORDER BY stage) AS stages,
               STRING_AGG(CAST(match_number AS VARCHAR), ', ' ORDER BY match_number) AS match_numbers_str
        FROM city_info
        GROUP BY city
        ORDER BY city
    """).fetchdf()


@st.cache_data
def get_city_knockout_stages(city: str) -> list[str]:
    """Get the knockout stages hosted in a specific city.

    Returns list of stage strings (e.g. ['ROUND_OF_32', 'ROUND_OF_16'])
    """
    con = get_db()
    result = con.execute("""
        SELECT stage, MIN(match_number) AS min_match
        FROM matches
        WHERE city = ? AND stage != 'GROUP_STAGE'
          AND sim_id = (SELECT MIN(sim_id) FROM matches)
        GROUP BY stage
        ORDER BY min_match
    """, [city]).fetchdf()
    return result["stage"].tolist()


@st.cache_data
def get_city_knockout_matchups(city: str, stage: str | None = None, limit: int = 5) -> pd.DataFrame:
    """Top matchups for knockout matches in a city.

    Returns DataFrame with columns: stage, match_number, team1, team2, count, probability
    """
    con = get_db()
    stage_filter = "AND stage = ?" if stage else ""
    params = [city] + ([stage] if stage else [])

    return con.execute(f"""
        WITH matchups AS (
            SELECT stage, match_number,
                CASE WHEN home_team < away_team THEN home_team ELSE away_team END AS team1,
                CASE WHEN home_team < away_team THEN away_team ELSE home_team END AS team2
            FROM matches
            WHERE city = ? AND stage != 'GROUP_STAGE' {stage_filter}
        )
        SELECT stage, match_number, team1, team2,
               COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {get_total_sims()}, 2) AS probability
        FROM matchups
        GROUP BY stage, match_number, team1, team2
        ORDER BY match_number, count DESC
    """, params).fetchdf()


@st.cache_data
def get_city_group_matches(city: str) -> pd.DataFrame:
    """Get group stage matches scheduled in a city (fixed schedule).

    Returns DataFrame with columns: match_number, group_name, home_team, away_team
    """
    con = get_db()
    return con.execute("""
        SELECT match_number, group_name, home_team, away_team
        FROM matches
        WHERE city = ? AND stage = 'GROUP_STAGE'
          AND sim_id = (SELECT MIN(sim_id) FROM matches)
        ORDER BY match_number
    """, [city]).fetchdf()
