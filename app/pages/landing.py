"""
Page 1 - Landing Page
FIFA World Cup 2026 Simulation Explorer
"""

import streamlit as st
from db.landing_queries import (
    get_champion_probs,
    get_runner_up_probs,
    get_third_place_probs,
)
from ui.cards import render_podium_card, render_stat_box, render_info_box

# --- Hero Section ---
st.markdown(
    """
<div class="wc-hero">
    <h1>FIFA World Cup 2026</h1>
    <p class="subtitle">
        We simulated the tournament <strong>100,000 times</strong> so you don't have to.
        Explore who's most likely to lift the trophy, which matchups await your team,
        and what games your city will host.
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# --- Load data ---
champions = get_champion_probs()
runners_up = get_runner_up_probs()
thirds = get_third_place_probs()

# --- Projected Podium ---
st.markdown(
    '<div class="wc-section-header">Projected Podium</div>', unsafe_allow_html=True
)
st.caption(
    "Based on 100,000 full tournament simulations using a model trained on past World Cup matches."
)

col1, col2, col3 = st.columns(3)

with col1:
    render_podium_card(
        position="Champion",
        team=champions.iloc[0]["team"],
        probability=champions.iloc[0]["probability"],
        css_class="wc-podium-gold",
        secondaries=[
            (champions.iloc[i]["team"], champions.iloc[i]["probability"])
            for i in range(1, min(3, len(champions)))
        ],
    )

with col2:
    render_podium_card(
        position="Runner-up",
        team=runners_up.iloc[0]["team"],
        probability=runners_up.iloc[0]["probability"],
        css_class="wc-podium-silver",
        secondaries=[
            (runners_up.iloc[i]["team"], runners_up.iloc[i]["probability"])
            for i in range(1, min(3, len(runners_up)))
        ],
    )

with col3:
    render_podium_card(
        position="3rd Place",
        team=thirds.iloc[0]["team"],
        probability=thirds.iloc[0]["probability"],
        css_class="wc-podium-bronze",
        secondaries=[
            (thirds.iloc[i]["team"], thirds.iloc[i]["probability"])
            for i in range(1, min(3, len(thirds)))
        ],
    )

st.markdown("<br>", unsafe_allow_html=True)

# --- Quick stats ---
s1, s2, s3, s4 = st.columns(4)
with s1:
    render_stat_box("48", "Teams")
with s2:
    render_stat_box("16", "Host Cities")
with s3:
    render_stat_box("104", "Matches per Tournament")
with s4:
    render_stat_box("100K", "Simulations")

st.markdown("<br>", unsafe_allow_html=True)

# --- How it works ---
# render_info_box(
#     "Each simulation uses a <strong>Poisson regression model</strong> trained on every World Cup match "
#     "from 1998 to 2022. The model predicts expected goals for each team based on FIFA rankings, "
#     "then simulates all 104 matches of the 2026 tournament — from the group stage through the final. "
#     "By running this 100,000 times, we get a rich picture of what's likely (and what's possible)."
# )

st.markdown("<br>", unsafe_allow_html=True)

# --- Call to Action ---
st.markdown(
    '<div class="wc-section-header">Explore the Data</div>', unsafe_allow_html=True
)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        """
    <a href="/competition" target="_self" style="text-decoration: none; color: inherit; display: block;">
        <div class="wc-cta-card wc-cta-turquoise">
            <div class="cta-icon">📊</div>
            <div class="cta-title">Competition Explorer</div>
            <div class="cta-desc">Dive into each round — from group stage to the final. See the most likely matchups and scores.</div>
            <div style="margin-top:0.5rem; font-weight:600; color:var(--wc-turquoise);">Explore the Competition &rarr;</div>
        </div>
    </a>
    """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
    <a href="/team" target="_self" style="text-decoration: none; color: inherit; display: block;">
        <div class="wc-cta-card wc-cta-magenta">
            <div class="cta-icon">⚽</div>
            <div class="cta-title">Team Explorer</div>
            <div class="cta-desc">Pick your team and follow their most likely tournament path. Who will they face?</div>
            <div style="margin-top:0.5rem; font-weight:600; color:var(--wc-magenta);">Find Your Team &rarr;</div>
        </div>
    </a>
    """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
    <a href="/city" target="_self" style="text-decoration: none; color: inherit; display: block;">
        <div class="wc-cta-card wc-cta-gold">
            <div class="cta-icon">🏙️</div>
            <div class="cta-title">City Explorer</div>
            <div class="cta-desc">Planning to attend? See which playoff matches are most likely in each host city.</div>
            <div style="margin-top:0.5rem; font-weight:600; color:#B8860B;">Pick Your City &rarr;</div>
        </div>
    </a>
    """,
        unsafe_allow_html=True,
    )
