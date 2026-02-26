"""
Page 2 - Competition Explorer
Explore each stage of the tournament from the Final down to the Group Stage.
"""

import streamlit as st
from db.competition_queries import (
    get_stage_matchups,
    get_matchup_results,
    get_all_groups_most_likely,
    get_group_most_likely_standings,
    get_group_scenarios,
    get_third_place_advancement,
    get_head_to_head,
    get_group_position_probabilities,
)
from db.team_queries import get_all_teams
from ui.cards import (
    render_match_card,
    render_score_row,
    render_info_box,
    render_group_standing_table,
    render_position_probabilities_heatmap,
)
from ui.flags import team_with_flag, get_flag
from config import (
    KNOCKOUT_STAGES_UI,
    KNOCKOUT_STAGE_LABELS,
    GROUP_NAMES,
    STAGE_DISPLAY_NAMES,
)

st.markdown(
    '<div class="wc-section-header">Competition Explorer</div>', unsafe_allow_html=True
)

render_info_box(
    "Explore every stage of the FIFA World Cup 2026 — from the Final down to the Group Stage. "
    "Select a round below to see the most likely matchups and click on any matchup to reveal "
    "the most probable scores."
)

# --- Stage selector ---
selected_stage = st.pills(
    "Select Stage",
    options=KNOCKOUT_STAGES_UI,
    format_func=lambda x: KNOCKOUT_STAGE_LABELS[x],
    default="FINAL",
)

if not selected_stage:
    selected_stage = "FINAL"

st.markdown("<br>", unsafe_allow_html=True)

# --- Head-to-Head view ---
if selected_stage == "HEAD_TO_HEAD":
    st.markdown(
        '<div class="wc-section-sub">Head-to-Head Knockout Matchup Analyzer</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Select any two teams to see how likely they are to meet in the **knockout stages**, "
        "which round they'd most likely clash in, and who has the edge if they do meet."
    )

    all_teams = get_all_teams()
    team_list = sorted(all_teams["team"].tolist())

    col_a, col_b = st.columns(2)
    with col_a:
        team_a = st.selectbox("Team A", team_list, index=0)
    with col_b:
        default_b = 1 if len(team_list) > 1 else 0
        team_b = st.selectbox("Team B", team_list, index=default_b)

    if team_a == team_b:
        st.warning("Please select two different teams.")
    else:
        h2h = get_head_to_head(team_a, team_b)

        if h2h is None:
            st.info(
                f"{team_with_flag(team_a)} and {team_with_flag(team_b)} never met "
                "in the knockout stages across all 100,000 simulations."
            )
        else:
            # Meeting probability
            flag_a = get_flag(team_a)
            flag_b = get_flag(team_b)
            st.markdown(f"""
            <div class="wc-card-flat" style="text-align:center; padding:1.25rem;">
                <div style="font-size:0.9rem; color:var(--wc-secondary); margin-bottom:0.5rem;">Meeting Probability</div>
                <div style="font-size:1rem; font-weight:600; margin-bottom:0.5rem;">
                    {flag_a} {team_a} vs {team_b} {flag_b}
                </div>
                <div style="font-size:2rem; font-weight:700; color:var(--wc-turquoise);">
                    {h2h['meeting_pct']:.1f}%
                </div>
                <div style="font-size:0.8rem; color:var(--wc-secondary); margin-top:0.25rem;">
                    Met in {h2h['meeting_count']:,} of 100,000 simulations
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Stage distribution and Win % side by side
            col_stage, col_win = st.columns([3, 2])

            with col_stage:
                st.markdown(
                    '<div class="wc-section-sub" style="font-size:1rem;">Stage Distribution</div>',
                    unsafe_allow_html=True,
                )
                tbl = '<div class="wc-card-flat"><table class="wc-group-table"><thead><tr>'
                tbl += '<th>Stage</th><th>Probability</th><th>Share</th>'
                tbl += '</tr></thead><tbody>'
                for s in h2h["stage_distribution"]:
                    tbl += '<tr>'
                    tbl += f'<td>{s["stage_label"]}</td>'
                    tbl += f'<td><strong>{s["abs_pct"]:.1f}%</strong></td>'
                    tbl += f'<td>{s["rel_pct"]:.1f}%</td>'
                    tbl += '</tr>'
                tbl += '</tbody></table></div>'
                st.markdown(tbl, unsafe_allow_html=True)

            with col_win:
                st.markdown(
                    '<div class="wc-section-sub" style="font-size:1rem;">Win Probability (if they meet)</div>',
                    unsafe_allow_html=True,
                )
                wp = h2h["win_pcts"]
                st.markdown(f"""
                <div class="wc-card-flat" style="padding:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
                        <div style="text-align:center; flex:1;">
                            <div style="font-size:1.5rem;">{flag_a}</div>
                            <div style="font-weight:600; font-size:0.9rem;">{wp['team1_name']}</div>
                            <div style="font-size:1.5rem; font-weight:700; color:var(--wc-turquoise);">{wp['team1_pct']:.1f}%</div>
                        </div>
                        <div style="font-size:0.9rem; color:var(--wc-secondary); padding:0 0.5rem;">vs</div>
                        <div style="text-align:center; flex:1;">
                            <div style="font-size:1.5rem;">{flag_b}</div>
                            <div style="font-weight:600; font-size:0.9rem;">{wp['team2_name']}</div>
                            <div style="font-size:1.5rem; font-weight:700; color:var(--wc-turquoise);">{wp['team2_pct']:.1f}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- Group Stage view ---
elif selected_stage == "GROUP_STAGE":
    group_view = st.radio(
        "View",
        ["All Groups Overview", "Specific Group", "Best 3rd-Place Teams"],
        horizontal=True,
    )

    if group_view == "All Groups Overview":
        st.markdown(
            '<div class="wc-section-sub">Most Likely Group Outcomes</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "For each group, this shows the single most likely final standing "
            "(the ordering that appeared most often across 100,000 simulations). "
            "Percentages represent the likelihood of this exact group standing order."
        )

        groups_data = get_all_groups_most_likely()

        # Display in a 4x3 grid
        for row_start in range(0, 12, 4):
            cols = st.columns(4)
            for i, col in enumerate(cols):
                grp_idx = row_start + i
                if grp_idx >= len(groups_data):
                    break
                grp_row = groups_data.iloc[grp_idx]
                group_name = grp_row["group_name"]
                team_order = grp_row["team_order"]
                prob = grp_row["probability"]

                with col:
                    rows = get_group_most_likely_standings(group_name, team_order)
                    if not rows:
                        teams = team_order.split(",")
                        rows = [
                            {"position": pos + 1, "team": team, "advanced": pos < 2}
                            for pos, team in enumerate(teams)
                        ]
                    render_group_standing_table(rows, group_name, prob, compact=True)

    elif group_view == "Specific Group":
        # Specific group selector
        selected_group = st.selectbox(
            "Select Group",
            GROUP_NAMES,
            format_func=lambda g: f"Group {g}",
        )

        # --- Position Probabilities Heatmap ---
        probs_df = get_group_position_probabilities(selected_group)
        render_position_probabilities_heatmap(probs_df)

        st.markdown(
            f'<div class="wc-section-sub">Top 5 Most Likely Outcomes for Group {selected_group}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Each scenario below shows a complete group outcome — the final standings that appeared "
            "most often across 100,000 simulations. Expand each to see the detailed table."
        )

        scenarios = get_group_scenarios(selected_group, limit=5)

        if not scenarios:
            st.info("No scenario data available.")
        else:
            for i, scenario in enumerate(scenarios):
                is_top = i == 0
                label = f"{'Most likely' if is_top else f'#{i+1}'}: {scenario['team_order']} — {scenario['probability']:.1f}%"
                with st.expander(label, expanded=is_top):
                    render_group_standing_table(
                        scenario["standings"],
                        selected_group,
                        scenario["probability"],
                    )

    else:
        # Best 3rd-Place Teams view
        st.markdown(
            '<div class="wc-section-sub">Best 3rd-Place Teams — Advancement Probability</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "In the 2026 format, the 8 best 3rd-place teams advance to the Round of 32. "
            "This shows how likely each team is to advance as a best 3rd-place finisher, "
            "and which groups are most likely to send their 3rd-place team through."
        )

        teams_df, groups_df = get_third_place_advancement()

        if teams_df.empty:
            st.info("No 3rd-place data available.")
        else:
            # Teams table
            st.markdown(
                '<div class="wc-section-sub" style="font-size:1rem;">Teams Most Likely to Advance</div>',
                unsafe_allow_html=True,
            )

            table_html = '<div class="wc-card-flat"><table class="wc-group-table"><thead><tr>'
            table_html += '<th>#</th><th>Team</th><th>Group</th><th>Adv %</th><th>Avg Pts</th><th>Avg GD</th>'
            table_html += '</tr></thead><tbody>'
            for idx, row in teams_df.iterrows():
                flag = get_flag(row["team"])
                table_html += '<tr class="advanced">'
                table_html += f'<td>{idx + 1}</td>'
                table_html += f'<td>{flag} {row["team"]}</td>'
                table_html += f'<td>{row["group_name"]}</td>'
                table_html += f'<td><strong>{row["adv_pct"]:.1f}%</strong></td>'
                table_html += f'<td>{row["avg_points"]}</td>'
                table_html += f'<td>{row["avg_gd"]}</td>'
                table_html += '</tr>'
            table_html += '</tbody></table></div>'
            st.markdown(table_html, unsafe_allow_html=True)

            # Groups table
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<div class="wc-section-sub" style="font-size:1rem;">Groups Most Likely to Send 3rd-Place Team Through</div>',
                unsafe_allow_html=True,
            )

            grp_html = '<div class="wc-card-flat"><table class="wc-group-table"><thead><tr>'
            grp_html += '<th>#</th><th>Group</th><th>Adv %</th>'
            grp_html += '</tr></thead><tbody>'
            for idx, row in groups_df.iterrows():
                grp_html += '<tr>'
                grp_html += f'<td>{idx + 1}</td>'
                grp_html += f'<td>Group {row["group_name"]}</td>'
                grp_html += f'<td><strong>{row["adv_pct"]:.1f}%</strong></td>'
                grp_html += '</tr>'
            grp_html += '</tbody></table></div>'
            st.markdown(grp_html, unsafe_allow_html=True)

# --- Knockout stage matchups ---
else:
    display_name = STAGE_DISPLAY_NAMES.get(selected_stage, selected_stage)
    st.markdown(
        f'<div class="wc-section-sub">Top 5 Most Likely {display_name} Matchups</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Showing the 5 most frequently occurring matchups across all 100,000 simulations."
    )

    matchups = get_stage_matchups(selected_stage, limit=5)

    if matchups.empty:
        st.info("No matchup data available for this stage.")
    else:
        for idx, row in matchups.iterrows():
            team1, team2, prob = row["team1"], row["team2"], row["probability"]
            render_match_card(team1, team2, prob)

            # Expandable score details
            with st.expander(
                f"See most likely scores for {team_with_flag(team1)} vs {team_with_flag(team2)}"
            ):
                scores = get_matchup_results(selected_stage, team1, team2, limit=8)
                if scores.empty:
                    st.write("No score data available.")
                else:
                    st.caption("Most probable scores when these two teams meet:")
                    for _, s in scores.iterrows():
                        render_score_row(
                            s["home_team"],
                            s["away_team"],
                            int(s["home_score"]),
                            int(s["away_score"]),
                            s["winner"],
                            s["probability"],
                        )
