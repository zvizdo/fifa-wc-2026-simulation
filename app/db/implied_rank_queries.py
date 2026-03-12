"""
Implied Polymarket Rank queries.

Uses marginal win-rate curves from 100k rank-randomized simulations and
log-ratio optimization with ordering constraints to find implied ranks.

For each team, we build a win_rate(rank) curve from thousands of simulation
samples per rank bin. The optimizer finds ranks where the win-rate SHARES
(ratios) between teams best match Polymarket's odds, constrained so that
teams with higher Polymarket odds get better (lower) implied ranks.
"""

import json
import logging
import os
from datetime import timedelta

import duckdb
import numpy as np
import streamlit as st
from scipy.interpolate import interp1d
from scipy.optimize import minimize

from db.polymarket_queries import get_polymarket_odds

logger = logging.getLogger(__name__)

RANK_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "wc2026_rank.duckdb"
)

TOP_N = 10  # Number of teams to optimize


@st.cache_data(ttl=timedelta(hours=8))
def get_implied_polymarket_ranks() -> dict[str, dict] | None:
    """Find implied Polymarket ranks via log-ratio marginal optimization.

    Returns a dict mapping team name -> {
        'implied_rank': float,
        'predicted_pct': float,   # model's predicted win % (rescaled)
        'polymarket_pct': float,  # polymarket target win %
        'delta': float,           # predicted - polymarket
    }, or None if data is unavailable.
    """
    poly_odds_raw = get_polymarket_odds()
    if not poly_odds_raw:
        return None
        
    poly_odds = {t: v["yes"] for t, v in poly_odds_raw.items()}

    if not os.path.exists(RANK_DB_PATH):
        logger.warning("Rank simulation DB not found at %s", RANK_DB_PATH)
        return None

    try:
        con = duckdb.connect(RANK_DB_PATH, read_only=True)

        # Get teams that actually exist in the rank simulation
        available = set(
            con.execute("SELECT DISTINCT team FROM sim_team_ranks").fetchdf()["team"]
        )

        # Take top N teams by Polymarket probability, filtered to available teams
        sorted_teams = sorted(
            ((t, p) for t, p in poly_odds.items() if t in available),
            key=lambda x: x[1], reverse=True,
        )[:TOP_N]
        top_teams = [t[0] for t in sorted_teams]
        target_probs = np.array([t[1] for t in sorted_teams])
        target_shares = target_probs / target_probs.sum()
        n_teams = len(top_teams)

        # Build per-team marginal win-rate curves
        curves = {}
        for team in top_teams:
            df = con.execute(f"""
                SELECT r.fifa_rank,
                       COUNT(*) as total_sims,
                       SUM(CASE WHEN m.winner = r.team THEN 1 ELSE 0 END) as wins
                FROM sim_team_ranks r
                JOIN matches m ON r.sim_id = m.sim_id AND m.stage = 'FINAL'
                WHERE r.team = '{team}'
                GROUP BY r.fifa_rank
                ORDER BY r.fifa_rank
            """).fetchdf()

            ranks = df["fifa_rank"].values.astype(float)
            win_pct = 100.0 * df["wins"].values / df["total_sims"].values

            f = interp1d(
                ranks, win_pct, kind="linear",
                fill_value=(win_pct[0], win_pct[-1]), bounds_error=False,
            )
            curves[team] = {
                "interp": f,
                "min_rank": float(ranks.min()),
                "max_rank": float(ranks.max()),
            }

        con.close()

    except Exception as e:
        logger.error("Failed to load rank simulation data: %s", e)
        return None

    # ── Optimization ──────────────────────────────────────────────────

    # Sort teams by polymarket odds (best first) — for ordering constraints
    pm_order = np.argsort(-target_probs)

    def eval_shares(rank_vec: np.ndarray):
        raw = np.array([
            max(0.001, float(curves[t]["interp"](rank_vec[i])))
            for i, t in enumerate(top_teams)
        ])
        return raw / raw.sum(), raw

    def objective(rank_vec: np.ndarray) -> float:
        shares, _ = eval_shares(rank_vec)

        # Log-ratio loss: penalises relative deviations equally
        log_pred = np.log(shares + 1e-10)
        log_target = np.log(target_shares + 1e-10)
        share_loss = float(np.sum((log_pred - log_target) ** 2))

        # Ordering penalty: higher Poly odds → lower (better) implied rank
        order_penalty = 0.0
        for k in range(len(pm_order) - 1):
            i, j = int(pm_order[k]), int(pm_order[k + 1])
            if rank_vec[i] >= rank_vec[j]:
                order_penalty += (rank_vec[i] - rank_vec[j] + 0.5) ** 2

        return share_loss + 0.5 * order_penalty

    # Initial guess: ranks spaced by polymarket ordering, starting at 1.0
    x0 = np.linspace(1.0, 35.0, n_teams)
    
    # Anchor the top Polymarket favorite to exact rank 1.0.
    # The rest are bounded between 1.0 and 80.0.
    bounds = [(1.0, 1.0)] + [(1.0, 80.0)] * (n_teams - 1)

    result = minimize(
        objective, x0, bounds=bounds, method="L-BFGS-B",
        options={"maxiter": 500, "ftol": 1e-14},
    )

    # Compute final predictions
    shares, _ = eval_shares(result.x)
    predicted_pct = shares * target_probs.sum()

    output = {}
    for i, team in enumerate(top_teams):
        output[team] = {
            "implied_rank": round(float(result.x[i]), 1),
            "predicted_pct": round(float(predicted_pct[i]), 1),
            "polymarket_pct": float(target_probs[i]),
            "delta": round(float(predicted_pct[i] - target_probs[i]), 1),
        }

    return output
