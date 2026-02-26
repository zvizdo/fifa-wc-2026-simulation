"""
Page 4 - City Explorer
Explore which matches and matchups are most likely in each of the 16 host cities.
"""
import streamlit as st
from db.city_queries import (
    get_city_overview,
    get_city_knockout_stages,
    get_city_knockout_matchups,
    get_city_group_matches,
)
from db.competition_queries import get_matchup_results
from ui.cards import render_match_card, render_score_row, render_info_box
from ui.flags import team_with_flag
from config import CITY_STADIUMS, STAGE_DISPLAY_NAMES

st.markdown('<div class="wc-section-header">City Explorer</div>', unsafe_allow_html=True)
render_info_box(
    "Planning to attend the World Cup? This page helps you figure out which matches "
    "are most likely in each of the 16 host cities across the USA, Mexico, and Canada. "
    "Especially useful for knockout rounds where the exact matchups aren't known yet."
)

# --- Load overview data ---
overview = get_city_overview()

# --- City selector ---
city_names = sorted(overview["city"].tolist())
selected_city = st.selectbox(
    "Select a city to explore",
    options=city_names,
    index=city_names.index("New York/New Jersey") if "New York/New Jersey" in city_names else 0,
)

if not selected_city:
    st.stop()

# --- City detail header ---
stadium_info = CITY_STADIUMS.get(selected_city, ("Unknown", 0))
city_row = overview[overview["city"] == selected_city].iloc[0]

st.markdown(f"""
<div class="wc-card" style="border-top:4px solid var(--wc-turquoise);">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
        <div>
            <h2 style="margin:0;">{selected_city}</h2>
            <div style="color:var(--wc-secondary);">{stadium_info[0]} &bull; {city_row['country']}</div>
        </div>
        <div style="display:flex; gap:2rem; text-align:center;">
            <div>
                <div style="font-size:1.5rem; font-weight:700; color:var(--wc-turquoise);">
                    {int(city_row['total_matches'])}
                </div>
                <div style="font-size:0.8rem; color:var(--wc-secondary);">Total Matches</div>
            </div>
            <div>
                <div style="font-size:1.5rem; font-weight:700; color:var(--wc-magenta);">
                    {int(city_row['num_knockout_matches'])}
                </div>
                <div style="font-size:0.8rem; color:var(--wc-secondary);">Knockout Matches</div>
            </div>
            <div>
                <div style="font-size:1.5rem; font-weight:700; color:var(--wc-gold);">
                    {stadium_info[1]:,}
                </div>
                <div style="font-size:0.8rem; color:var(--wc-secondary);">Capacity</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Group stage matches (fixed) ---
group_matches = get_city_group_matches(selected_city)
if not group_matches.empty:
    with st.expander(f"Group Stage Matches ({len(group_matches)} matches)", expanded=False):
        st.caption("Group stage matchups are fixed by the draw — these teams are guaranteed to play here.")
        for _, match in group_matches.iterrows():
            home = match["home_team"]
            away = match["away_team"]
            group = match["group_name"]
            st.markdown(f"""
            <div class="wc-card-flat" style="display:flex; align-items:center; justify-content:space-between; padding:0.6rem 1rem;">
                <span class="wc-badge wc-badge-turquoise">Match {int(match['match_number'])}</span>
                <span style="font-weight:600;">{team_with_flag(home)} vs {team_with_flag(away)}</span>
                <span class="wc-badge wc-badge-gold">Group {group}</span>
            </div>
            """, unsafe_allow_html=True)

# --- Knockout matchups by stage ---
knockout_stages = get_city_knockout_stages(selected_city)

if not knockout_stages:
    st.info("This city does not host any knockout stage matches.")
else:
    st.markdown('<div class="wc-section-sub">Knockout Stage Matchups</div>', unsafe_allow_html=True)
    st.caption(
        "Unlike the group stage, knockout matchups depend on results. "
        "Below are the most likely matchups for each knockout round hosted here."
    )

    if len(knockout_stages) > 1:
        tabs = st.tabs([STAGE_DISPLAY_NAMES.get(s, s) for s in knockout_stages])
    else:
        tabs = [st.container()]

    for tab, stage_key in zip(tabs, knockout_stages):
        with tab:
            all_matchups = get_city_knockout_matchups(selected_city, stage_key, limit=5)

            if all_matchups.empty:
                st.write("No knockout matchup data for this stage.")
                continue

            # Group by match number
            for match_num in sorted(all_matchups["match_number"].unique()):
                match_data = all_matchups[all_matchups["match_number"] == match_num]
                display_stage = STAGE_DISPLAY_NAMES.get(stage_key, stage_key)

                st.markdown(
                    f'<div style="font-size:0.85rem; color:var(--wc-secondary); margin-top:1rem;">'
                    f'Match #{int(match_num)} &mdash; {display_stage}</div>',
                    unsafe_allow_html=True,
                )

                # Show top 5 matchups for this match number
                for _, row in match_data.head(5).iterrows():
                    team1 = row["team1"]
                    team2 = row["team2"]
                    prob = row["probability"]
                    render_match_card(team1, team2, prob)

                    with st.expander(f"Scores: {team_with_flag(team1)} vs {team_with_flag(team2)}"):
                        scores = get_matchup_results(stage_key, team1, team2, limit=6)
                        if scores.empty:
                            st.write("No score data available.")
                        else:
                            for _, s in scores.iterrows():
                                render_score_row(
                                    s["home_team"], s["away_team"],
                                    int(s["home_score"]), int(s["away_score"]),
                                    s["winner"], s["probability"],
                                )
