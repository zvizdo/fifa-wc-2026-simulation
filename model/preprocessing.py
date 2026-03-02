"""Preprocessing functions for tournament history feature engineering.

Processes matches chronologically within each tournament to compute
dynamic ranks (general, offensive, defensive) and derived features.
"""

import numpy as np
import pandas as pd


STRONG_CONFEDS = {"UEFA", "CONMEBOL"}


def calculate_rank_shift(rank_a, rank_b, result, shape=1.5, k_mul=5):
    """Calculate Elo-style rank shift for general rank.

    Parameters
    ----------
    rank_a : float
        Current rank of the team.
    rank_b : float
        Current rank of the opponent.
    result : float
        Match result from team A's perspective (1=win, 0.5=draw, 0=loss).
    shape : float
        Exponent controlling win-expectation curve steepness.
    k_mul : float
        Multiplier for the k-factor (controls shift magnitude).

    Returns
    -------
    float
        Rank shift value. Positive = rank worsens (number increases),
        negative = rank improves (number decreases).
    """
    r_a = max(1.0, rank_a)
    r_b = max(1.0, rank_b)
    expected_a = 1 / (1 + (r_a / r_b) ** shape)
    k_factor = np.log1p(abs(r_a - r_b)) * k_mul
    shift = k_factor * (expected_a - result)
    return shift


def calculate_off_rank_shift(off_rank, opp_cur_rank, goals_scored,
                             shape=1.5, k_off_mul=5, goal_cap=4.0):
    """Calculate offensive rank shift based on goals scored.

    Scoring more goals than expected (given offensive rank vs opponent
    quality) improves (lowers) the offensive rank.

    Parameters
    ----------
    off_rank : float
        Current offensive rank of the team.
    opp_cur_rank : float
        Current general rank of the opponent.
    goals_scored : int
        Goals scored by the team in this match.
    shape : float
        Exponent for the expectation formula.
    k_off_mul : float
        Multiplier for the k-factor.
    goal_cap : float
        Maximum goals for normalization to [0, 1].
    """
    r_a = max(1.0, off_rank)
    r_b = max(1.0, opp_cur_rank)
    expected = 1 / (1 + (r_a / r_b) ** shape)
    actual = min(goals_scored / goal_cap, 1.0)
    k_factor = np.log1p(abs(r_a - r_b)) * k_off_mul
    shift = k_factor * (expected - actual)
    return shift


def calculate_def_rank_shift(def_rank, opp_cur_rank, goals_conceded,
                             shape=1.5, k_def_mul=5, goal_cap=4.0):
    """Calculate defensive rank shift based on goals conceded.

    Conceding fewer goals than expected improves (lowers) defensive rank.
    Conceding against weaker opponents is penalized more heavily because
    the expected performance gap (k_factor) is larger.

    Parameters
    ----------
    def_rank : float
        Current defensive rank of the team.
    opp_cur_rank : float
        Current general rank of the opponent.
    goals_conceded : int
        Goals conceded by the team in this match.
    shape : float
        Exponent for the expectation formula.
    k_def_mul : float
        Multiplier for the k-factor.
    goal_cap : float
        Maximum goals for normalization to [0, 1].
    """
    r_a = max(1.0, def_rank)
    r_b = max(1.0, opp_cur_rank)
    expected = 1 / (1 + (r_a / r_b) ** shape)
    # Invert: 0 goals conceded = best defense (1.0), goal_cap conceded = worst (0.0)
    actual = 1.0 - min(goals_conceded / goal_cap, 1.0)
    k_factor = np.log1p(abs(r_a - r_b)) * k_def_mul
    shift = k_factor * (expected - actual)
    return shift


def process_tournament_history(df_base, shape=1.5, k_mul=5,
                               k_off_mul=5, k_def_mul=5, goal_cap=4.0):
    """Process all tournaments chronologically, computing dynamic features.

    For each team within each tournament, tracks:
    - cur_rank: General dynamic rank (Elo-style, based on match results)
    - off_rank: Offensive rank (based on goals scored vs opponent quality)
    - def_rank: Defensive rank (based on goals conceded vs opponent quality)

    Derived features added:
    - rank_shift: cur_rank - rank (team form / momentum)
    - opp_rank_shift: Same for opponent
    - rest_diff: lst_match_days_ago - opp_lst_match_days_ago
    - is_strong_confed / opp_is_strong_confed: confederation grouping

    Parameters
    ----------
    df_base : pd.DataFrame
        Raw dataset with columns: tournament_id, match_id, match_date,
        team, opp_team, rank, opp_rank, score, win, draw,
        lst_match_days_ago, opp_lst_match_days_ago, confederation,
        opp_confederation, host.
    shape : float
        Exponent for all rank shift expectation formulas.
    k_mul : float
        Multiplier for general rank shift k-factor.
    k_off_mul : float
        Multiplier for offensive rank shift k-factor.
    k_def_mul : float
        Multiplier for defensive rank shift k-factor.
    goal_cap : float
        Cap for normalizing goals to [0, 1] in off/def calculations.

    Returns
    -------
    pd.DataFrame
        Sorted copy of df_base with added columns: cur_rank, opp_cur_rank,
        off_rank, opp_off_rank, def_rank, opp_def_rank, rank_shift,
        opp_rank_shift, rest_diff, is_strong_confed, opp_is_strong_confed.
    """
    df_sorted = df_base.sort_values(
        ["tournament_id", "match_date", "team", "opp_team"]
    ).copy()

    # Pre-compute goals conceded for each row by pairing match rows
    goals_conceded_map = {}
    for _, group in df_sorted.groupby("match_id"):
        indices = group.index.tolist()
        scores = group["score"].tolist()
        if len(indices) == 2:
            goals_conceded_map[indices[0]] = scores[1]
            goals_conceded_map[indices[1]] = scores[0]

    # State dictionaries keyed by (tournament_id, team_name)
    current_ranks = {}
    offensive_ranks = {}
    defensive_ranks = {}

    # Collect per-row values (at kickoff, before this match updates)
    cur_rank_list = []
    opp_cur_rank_list = []
    off_rank_list = []
    opp_off_rank_list = []
    def_rank_list = []
    opp_def_rank_list = []

    for i, row in df_sorted.iterrows():
        t_id = row["tournament_id"]
        t_name = row["team"]
        o_name = row["opp_team"]

        # Get current ranks at kickoff (default to base rank)
        r_a = current_ranks.get((t_id, t_name), float(row["rank"]))
        r_b = current_ranks.get((t_id, o_name), float(row["opp_rank"]))

        off_a = offensive_ranks.get((t_id, t_name), float(row["rank"]))
        off_b = offensive_ranks.get((t_id, o_name), float(row["opp_rank"]))

        def_a = defensive_ranks.get((t_id, t_name), float(row["rank"]))
        def_b = defensive_ranks.get((t_id, o_name), float(row["opp_rank"]))

        # Record kickoff values
        cur_rank_list.append(r_a)
        opp_cur_rank_list.append(r_b)
        off_rank_list.append(off_a)
        opp_off_rank_list.append(off_b)
        def_rank_list.append(def_a)
        opp_def_rank_list.append(def_b)

        # --- Update general rank ---
        result = float(row["win"] + 0.5 * row["draw"])
        gen_shift = calculate_rank_shift(r_a, r_b, result, shape, k_mul)
        current_ranks[(t_id, t_name)] = max(1.0, round(r_a + gen_shift, 1))

        # --- Update offensive rank ---
        goals_scored = row["score"]
        off_shift = calculate_off_rank_shift(
            off_a, r_b, goals_scored, shape, k_off_mul, goal_cap
        )
        offensive_ranks[(t_id, t_name)] = max(1.0, round(off_a + off_shift, 1))

        # --- Update defensive rank ---
        goals_conceded = goals_conceded_map.get(i, 0)
        def_shift = calculate_def_rank_shift(
            def_a, r_b, goals_conceded, shape, k_def_mul, goal_cap
        )
        defensive_ranks[(t_id, t_name)] = max(1.0, round(def_a + def_shift, 1))

    # Add computed columns
    df_sorted["cur_rank"] = cur_rank_list
    df_sorted["opp_cur_rank"] = opp_cur_rank_list
    df_sorted["off_rank"] = off_rank_list
    df_sorted["opp_off_rank"] = opp_off_rank_list
    df_sorted["def_rank"] = def_rank_list
    df_sorted["opp_def_rank"] = opp_def_rank_list

    # Derived features
    df_sorted["rank_shift"] = df_sorted["cur_rank"] - df_sorted["rank"]
    df_sorted["opp_rank_shift"] = df_sorted["opp_cur_rank"] - df_sorted["opp_rank"]
    df_sorted["rest_diff"] = (
        df_sorted["lst_match_days_ago"] - df_sorted["opp_lst_match_days_ago"]
    )
    df_sorted["is_strong_confed"] = (
        df_sorted["confederation"].isin(STRONG_CONFEDS).astype(int)
    )
    df_sorted["opp_is_strong_confed"] = (
        df_sorted["opp_confederation"].isin(STRONG_CONFEDS).astype(int)
    )

    # Stage weight: 0 = group stage, 1 = round of 16 / quarter-finals / third-place,
    # 2 = semi-finals / final
    stage_map = {
        "group stage": 0,
        "round of 16": 1,
        "quarter-finals": 1,
        "third-place match": 1,
        "semi-finals": 2,
        "final": 2,
    }
    df_sorted["stage_weight"] = df_sorted["stage_name"].map(stage_map).fillna(1).astype(int)

    return df_sorted
