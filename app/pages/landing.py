"""
Page 1 - Landing Page
FIFA World Cup 2026 Simulation Explorer
"""

import streamlit as st
from db.landing_queries import (
    get_champion_probs,
    get_most_likely_final,
    get_dark_horse,
)
from ui.cards import render_story_card, render_stat_box, render_info_box
from ui.flags import get_flag

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
champions = get_champion_probs(limit=1)
most_likely_final = get_most_likely_final()
dark_horse = get_dark_horse(rank_cutoff=15)

# --- Simulation Storylines ---
st.markdown(
    '<div class="wc-section-header">Simulation Storylines</div>', unsafe_allow_html=True
)
st.caption(
    "Based on 100,000 full tournament simulations using a model trained on past World Cup matches."
)

col1, col2, col3 = st.columns(3)

with col1:
    team = champions.iloc[0]["team"]
    prob = champions.iloc[0]["probability"]
    flag = get_flag(team)
    content = (
        '<div style="text-align: center; margin-bottom: 0.5rem;">'
        f'<div style="font-size: 3.5rem;">{flag}</div>'
        f'<div style="font-size: 1.8rem; font-weight: 700; margin: 0.5rem 0;">{team}</div>'
        f'<div style="color: var(--wc-turquoise); font-size: 1.8rem; font-weight: 800;">{prob:.1f}%</div>'
        '</div>'
    )
    render_story_card(
        title="The Favorite",
        subtitle="Team with the highest probability to lift the trophy.",
        content_html=content,
        css_class="wc-podium-gold"
    )

with col2:
    team1 = most_likely_final.iloc[0]["team1"]
    team2 = most_likely_final.iloc[0]["team2"]
    prob = most_likely_final.iloc[0]["probability"]
    flag1 = get_flag(team1)
    flag2 = get_flag(team2)
    content = (
        '<div style="text-align: center; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">'
        '<div style="text-align: right;">'
        f'<div style="font-size: 2.2rem;">{flag1}</div>'
        f'<div style="font-size: 1rem; font-weight: 700; margin-top: 0.2rem;">{team1}</div>'
        '</div>'
        '<div style="font-size: 1.2rem; font-weight: 800; color: var(--wc-secondary); margin: 0 0.5rem;">vs</div>'
        '<div style="text-align: left;">'
        f'<div style="font-size: 2.2rem;">{flag2}</div>'
        f'<div style="font-size: 1rem; font-weight: 700; margin-top: 0.2rem;">{team2}</div>'
        '</div>'
        '</div>'
        f'<div style="text-align: center; color: var(--wc-turquoise); font-size: 1.6rem; font-weight: 800; margin-top: 1rem;">{prob:.1f}%</div>'
    )
    render_story_card(
        title="Most Likely Final",
        subtitle="The single most probable matchup in the championship game.",
        content_html=content,
        css_class="wc-podium-silver"
    )

with col3:
    team = dark_horse.iloc[0]["team"]
    prob = dark_horse.iloc[0]["probability"]
    rank = dark_horse.iloc[0]["fifa_rank"]
    flag = get_flag(team)
    content = (
        '<div style="text-align: center; margin-bottom: 0.5rem;">'
        f'<div style="font-size: 3.5rem;">{flag}</div>'
        f'<div style="font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0 0.2rem 0;">{team}</div>'
        f'<div style="font-size: 0.9rem; color: var(--wc-secondary); font-weight: 600; margin-bottom: 0.5rem;">Pre-Tournament Rank: {rank}</div>'
        f'<div style="color: var(--wc-turquoise); font-size: 1.6rem; font-weight: 800;">{prob:.1f}%</div>'
        '</div>'
    )
    render_story_card(
        title="The Dark Horse",
        subtitle="Team ranked outside Top 15 with highest chance to reach Semi-Finals.",
        content_html=content,
        css_class="wc-podium-bronze"
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

st.markdown("<br><br>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.page_link("pages/about.py", label="ℹ️ About the Project", width="stretch")
