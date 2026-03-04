"""
Database queries for the Simulator page.
Queries run against the user's in-memory DuckDB (N simulations).
These do NOT use @st.cache_data because the in-memory DB changes each run.
"""
import pandas as pd
import duckdb
import streamlit as st


def get_user_champion_probs(con: duckdb.DuckDBPyConnection,
                            num_sims: int, limit: int = 10) -> pd.DataFrame:
    """Top N most likely champions from user simulations.

    Returns DataFrame with columns: team, count, probability
    """
    return con.execute(f"""
        SELECT winner AS team, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {num_sims}, 2) AS probability
        FROM matches
        WHERE match_number = 104
        GROUP BY winner
        ORDER BY count DESC
        LIMIT ?
    """, [limit]).fetchdf()


def get_user_runner_up_probs(con: duckdb.DuckDBPyConnection,
                             num_sims: int, limit: int = 10) -> pd.DataFrame:
    """Top N most likely runners-up from user simulations."""
    return con.execute(f"""
        SELECT
            CASE WHEN winner = home_team THEN away_team ELSE home_team END AS team,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / {num_sims}, 2) AS probability
        FROM matches
        WHERE match_number = 104
        GROUP BY team
        ORDER BY count DESC
        LIMIT ?
    """, [limit]).fetchdf()


def get_user_third_place_probs(con: duckdb.DuckDBPyConnection,
                               num_sims: int, limit: int = 10) -> pd.DataFrame:
    """Top N most likely 3rd-place finishers from user simulations."""
    return con.execute(f"""
        SELECT winner AS team, COUNT(*) AS count,
               ROUND(COUNT(*) * 100.0 / {num_sims}, 2) AS probability
        FROM matches
        WHERE match_number = 103
        GROUP BY winner
        ORDER BY count DESC
        LIMIT ?
    """, [limit]).fetchdf()


def get_user_group_standings(con: duckdb.DuckDBPyConnection,
                             num_sims: int,
                             group_name: str) -> list[dict]:
    """Most likely group finishing order from user simulations.

    Returns list of dicts: position, team, probability, advanced
    """
    result = con.execute(f"""
        WITH group_outcomes AS (
            SELECT sim_id,
                STRING_AGG(team, ',' ORDER BY position) AS team_order
            FROM group_standings
            WHERE group_name = ?
            GROUP BY sim_id
        ),
        counted AS (
            SELECT team_order, COUNT(*) AS count,
                   ROUND(COUNT(*) * 100.0 / {num_sims}, 2) AS probability
            FROM group_outcomes
            GROUP BY team_order
            ORDER BY count DESC
            LIMIT 1
        )
        SELECT team_order, probability
        FROM counted
    """, [group_name]).fetchdf()

    if result.empty:
        return []

    team_order = result.iloc[0]["team_order"]
    probability = result.iloc[0]["probability"]
    teams = team_order.split(",")

    return [
        {
            "position": pos + 1,
            "team": team,
            "probability": probability,
            "advanced": pos < 2,
        }
        for pos, team in enumerate(teams)
    ]


def get_user_stage_reach_probs(con: duckdb.DuckDBPyConnection,
                               num_sims: int,
                               team: str) -> pd.DataFrame:
    """Stage reach probabilities for a team from user simulations.

    Returns DataFrame with columns: stage, probability
    """
    knockout_probs = con.execute(f"""
        SELECT stage, COUNT(DISTINCT sim_id) AS appearances,
               ROUND(COUNT(DISTINCT sim_id) * 100.0 / {num_sims}, 2) AS probability
        FROM matches
        WHERE (home_team = ? OR away_team = ?) AND stage != 'GROUP_STAGE'
        GROUP BY stage
    """, [team, team]).fetchdf()

    champion = con.execute("""
        SELECT COUNT(*) AS cnt FROM matches
        WHERE match_number = 104 AND winner = ?
    """, [team]).fetchone()[0]
    champion_pct = round(champion * 100.0 / num_sims, 2)

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
        rows.append({"stage": stage_key, "display_name": display, "probability": prob})

    rows.append({"stage": "CHAMPION", "display_name": "Champion", "probability": champion_pct})

    return pd.DataFrame(rows)


def get_user_all_team_best_finish(con: duckdb.DuckDBPyConnection,
                                  num_sims: int) -> pd.DataFrame:
    """Average tournament depth score and champion probability for all teams.

    Stage scores: GROUP=0, R32=1, R16=2, QF=3, SF=4, FINAL=5, CHAMPION=6
    Returns DataFrame with columns: team, avg_stage_score, champ_prob
    """
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
               COALESCE(ROUND(c.wins * 100.0 / {num_sims}, 2), 0) AS champ_prob
        FROM combined_scores cs
        LEFT JOIN champs c ON c.team = cs.team
        GROUP BY cs.team, c.wins
        ORDER BY avg_stage_score DESC
    """).fetchdf()
