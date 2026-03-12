"""
Polymarket API queries for FIFA World Cup 2026 winner odds.

Uses the Gamma API (https://gamma-api.polymarket.com) to fetch
live prediction market odds. Results are cached for 8 hours.
"""

import json
import logging
from datetime import timedelta

import requests
import streamlit as st

logger = logging.getLogger(__name__)

POLYMARKET_EVENT_SLUG = "2026-fifa-world-cup-winner-595"
GAMMA_API_URL = f"https://gamma-api.polymarket.com/events?slug={POLYMARKET_EVENT_SLUG}"


@st.cache_data(ttl=timedelta(hours=8))
def get_polymarket_odds() -> dict[str, float]:
    """Fetch current Polymarket odds for the 2026 FIFA World Cup winner.

    Returns a dict mapping team name -> {"yes": prob, "no": prob} (as percentage, e.g. 15.5).
    Cached for 8 hours to avoid hammering the API.
    """
    try:
        resp = requests.get(GAMMA_API_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            logger.warning("Polymarket API returned empty response")
            return {}

        event = data[0]
        markets = event.get("markets", [])

        odds: dict[str, dict[str, float]] = {}
        for market in markets:
            # Skip inactive, closed, or placeholder markets
            if not market.get("active") or market.get("closed"):
                continue

            team_name = market.get("groupItemTitle", "")
            # Skip placeholder / "Other" / "Team XX" entries
            if not team_name or team_name.startswith("Team ") or team_name == "Other":
                continue

            outcome_prices_raw = market.get("outcomePrices", "[]")
            outcome_prices = json.loads(outcome_prices_raw)
            if outcome_prices and len(outcome_prices) >= 2:
                # First price is the "Yes" outcome probability, second is "No"
                prob_yes = float(outcome_prices[0]) * 100
                prob_no = float(outcome_prices[1]) * 100
                if prob_yes > 0:
                    odds[team_name] = {"yes": round(prob_yes, 1), "no": round(prob_no, 1)}

        return odds

    except Exception as e:
        logger.error(f"Failed to fetch Polymarket odds: {e}")
        return {}
