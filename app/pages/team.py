"""
Page 3 - Team Explorer
Select a team and explore their most likely tournament paths and opponents.
"""
import streamlit as st
from db.team_queries import (
    get_all_teams,
    get_team_outcome_distribution,
    get_team_stage_reach_probs,
    get_team_group_position_probs,
    get_team_opponents,
    get_team_info,
)
from ui.cards import render_info_box
from ui.brackets import render_team_pipeline
from ui.charts import create_outcome_bar_chart, create_opponent_bar_chart
from ui.flags import team_with_flag, get_flag
from config import STAGE_DISPLAY_NAMES

st.markdown('<div class="wc-section-header">Team Explorer</div>', unsafe_allow_html=True)
render_info_box(
    "Select any of the 48 competing teams to see their projected tournament path. "
    "How far are they likely to go? Who will they face? Explore the probabilities below."
)

# --- Team selector ---
all_teams = get_all_teams()

# Build options grouped by group
team_options = []
for _, row in all_teams.iterrows():
    team_options.append(row["team"])

# Format function shows flag + group
def format_team(t):
    info = all_teams[all_teams["team"] == t]
    if info.empty:
        return t
    grp = info.iloc[0]["group_name"]
    rank = info.iloc[0]["fifa_rank"]
    return f"{team_with_flag(t)} (Group {grp}, Rank {rank})"

selected_team = st.selectbox(
    "Choose a team",
    options=team_options,
    index=team_options.index("Spain") if "Spain" in team_options else 0,
    format_func=format_team,
)

if not selected_team:
    st.stop()

# --- Team header ---
info = get_team_info(selected_team)
flag = get_flag(selected_team)

st.markdown(f"""
<div class="wc-card" style="text-align:center; border-top:4px solid var(--wc-turquoise);">
    <span style="font-size:3rem;">{flag}</span>
    <h2 style="margin:0.25rem 0;">{selected_team}</h2>
    <div style="color:var(--wc-secondary);">
        Group {info['group_name']} &bull; FIFA Rank #{info['fifa_rank']} &bull; {info['confederation']}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Tournament Pipeline ---
st.markdown('<div class="wc-section-sub">Tournament Path — Stage-by-Stage Probability</div>',
            unsafe_allow_html=True)
st.caption(
    "This shows the probability of the team reaching each stage. "
    "Read left to right to see how far they're likely to go."
)

stage_probs = get_team_stage_reach_probs(selected_team)

# Build pipeline data — filter to key stages
pipeline_stages = ["GROUP_STAGE", "ROUND_OF_32", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL", "CHAMPION"]
pipeline_data = []
for s in pipeline_stages:
    row = stage_probs[stage_probs["stage"] == s]
    if not row.empty:
        prob = float(row["probability"].iloc[0])
        pipeline_data.append({
            "stage": s,
            "display_name": row["display_name"].iloc[0],
            "probability": prob,
            "reached": prob > 0,
        })
    else:
        display_name = STAGE_DISPLAY_NAMES.get(s, s)
        if s == "CHAMPION":
            display_name = "Champion"
        pipeline_data.append({
            "stage": s,
            "display_name": display_name,
            "probability": 0.0,
            "reached": False,
        })

render_team_pipeline(pipeline_data)

st.markdown("<br>", unsafe_allow_html=True)

# --- Outcome distribution ---
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown('<div class="wc-section-sub">Outcome Distribution</div>', unsafe_allow_html=True)
    st.caption("How often does the team finish in each position across 100,000 simulations?")

    outcomes = get_team_outcome_distribution(selected_team)
    if not outcomes.empty:
        fig = create_outcome_bar_chart(outcomes, selected_team)
        st.plotly_chart(fig, width="stretch")

with col_right:
    st.markdown('<div class="wc-section-sub">Group Stage Finish</div>', unsafe_allow_html=True)
    st.caption(f"How often does {selected_team} finish at each position in Group {info['group_name']}?")

    group_pos = get_team_group_position_probs(selected_team)
    if not group_pos.empty:
        for _, row in group_pos.iterrows():
            pos = int(row["position"])
            prob = row["probability"]
            label = f"{'1st' if pos == 1 else '2nd' if pos == 2 else '3rd' if pos == 3 else '4th'} Place"
            adv_note = " (advances)" if pos <= 2 else " (3rd — may advance)" if pos == 3 else ""
            color = "var(--wc-turquoise)" if pos <= 2 else "var(--wc-gold)" if pos == 3 else "var(--wc-secondary)"
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.5rem;">
                <div style="min-width:90px; font-weight:600; color:{color};">{label}{adv_note}</div>
                <div style="flex:1;">
                    <div class="wc-prob-bar-container">
                        <div class="wc-prob-bar" style="width:{min(prob, 100)}%;"></div>
                    </div>
                </div>
                <div style="min-width:50px; text-align:right; font-weight:600;">{prob:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Stage-by-stage opponents ---
st.markdown('<div class="wc-section-sub">Likely Opponents by Stage</div>', unsafe_allow_html=True)
st.caption(
    "For each knockout stage the team can reach, see their most likely opponents and head-to-head record."
)

knockout_stages = ["ROUND_OF_32", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]

for stage_key in knockout_stages:
    stage_row = stage_probs[stage_probs["stage"] == stage_key]
    if stage_row.empty or float(stage_row["probability"].iloc[0]) == 0:
        continue

    display = STAGE_DISPLAY_NAMES.get(stage_key, stage_key)
    prob = float(stage_row["probability"].iloc[0])

    with st.expander(f"{display} (reaches {prob:.1f}% of simulations)"):
        opponents = get_team_opponents(selected_team, stage_key, limit=8)
        if opponents.empty:
            st.write("No opponent data available.")
        else:
            for _, opp_row in opponents.iterrows():
                opp = opp_row["opponent"]
                opp_flag = get_flag(opp)
                total = int(opp_row["total"])
                wins = int(opp_row["wins"])
                losses = int(opp_row["losses"])
                matchup_pct = opp_row["matchup_pct"]
                win_rate = opp_row["win_rate"]

                st.markdown(f"""
                <div class="wc-card-flat" style="display:flex; align-items:center; gap:1rem; padding:0.75rem 1rem;">
                    <div style="font-size:1.1rem; min-width:180px; font-weight:600;">
                        {opp_flag} {opp}
                    </div>
                    <div style="flex:1; display:flex; gap:1.5rem; font-size:0.85rem; color:var(--wc-secondary);">
                        <span>Frequency: <strong style="color:var(--wc-dark);">{matchup_pct:.1f}%</strong></span>
                        <span>Record: <strong style="color:var(--wc-turquoise);">{wins}W</strong>-<strong style="color:var(--wc-magenta);">{losses}L</strong></span>
                        <span>Win rate: <strong style="color:var(--wc-dark);">{win_rate:.0f}%</strong></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
