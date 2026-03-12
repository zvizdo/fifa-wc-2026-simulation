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
from db.landing_queries import get_champion_probs
from db.polymarket_queries import get_polymarket_odds
from db.implied_rank_queries import get_implied_polymarket_ranks
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
winner_stages = ["WINNER"] + KNOCKOUT_STAGES_UI
winner_labels = {"WINNER": "🏆 Winner", **KNOCKOUT_STAGE_LABELS}

selected_stage = st.pills(
    "Select Stage",
    options=winner_stages,
    format_func=lambda x: winner_labels[x],
    default="WINNER",
)

if not selected_stage:
    selected_stage = "WINNER"

st.markdown("<br>", unsafe_allow_html=True)

# --- Winner view ---
if selected_stage == "WINNER":
    st.markdown(
        '<div class="wc-section-sub">Most Likely Champions</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Top 10 teams most likely to win the FIFA World Cup 2026 based on 100,000 simulations, "
        "compared with live prediction market odds from Polymarket."
    )

    view_mode = st.radio(
        "View Mode",
        options=["🏆 Simulation Results", "📈 Implied Ranks", "💰 Value Bets"],
        horizontal=True,
        label_visibility="collapsed"
    )
    poly_odds = get_polymarket_odds()

    # Load actual FIFA ranks
    import json, os
    teams_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data", "wc_2026_teams.json",
    )
    actual_ranks = {}
    try:
        with open(teams_path) as f:
            td = json.load(f)
        actual_ranks = {t["name"]: t["fifa_rank"] for g in td["groups"].values() for t in g}
    except Exception:
        pass

    if view_mode == "📈 Implied Ranks":
        render_info_box(
            "<strong>What is an Implied Rank?</strong> It translates the betting market's odds into a FIFA ranking. "
            "If a team has a <strong>lower (better) Implied Rank</strong> than their actual FIFA rank, the betting market "
            "thinks they are <strong>undervalued</strong> by FIFA and are stronger than their official ranking suggests. "
            "If it's higher, the market thinks they are overvalued. <br><br>We calculate this by finding the exact "
            "ranking configuration our simulation model would need to perfectly reproduce Polymarket's win probabilities.<br><br>"
            "<strong>Note on Rank Spacing:</strong> The top market favorite (Spain) is anchored to Rank 1.0 to normalize the rankings. "
            "Because betting markets assign an extremely high margin of probability to the few top favorites compared to the rest of the field, "
            "the model must push the implied ranks of lower-tier teams considerably further down to match their proportionally smaller win shares."
        )

        implied = get_implied_polymarket_ranks()
        if implied is None:
            st.info("Implied rank data is unavailable. Ensure the rank simulation DB exists.")
        else:
            sorted_implied = sorted(
                implied.items(), key=lambda x: x[1]["polymarket_pct"], reverse=True
            )

            for idx, (team, data) in enumerate(sorted_implied):
                flag_t = get_flag(team)
                actual = actual_ranks.get(team, "–")
                imp = data["implied_rank"]
                poly = data["polymarket_pct"]
                
                # Rank delta
                if isinstance(actual, int):
                    rank_delta = round(imp - actual, 1)
                    rd_color = "#22C55E" if rank_delta < 0 else "#EF4444" if rank_delta > 0 else "var(--wc-secondary)"
                    rd_sign = "+" if rank_delta > 0 else ""
                    rank_delta_str = f'<span style="color:{rd_color}; font-weight:600;">{rd_sign}{rank_delta}</span>'
                else:
                    rank_delta_str = "–"

                # Rank badge
                rank = idx + 1
                rank_colors = {
                    1: ("var(--wc-gold)", "#000"),
                    2: ("#C0C0C0", "#000"),
                    3: ("#CD7F32", "#fff"),
                }
                badge_bg, badge_fg = rank_colors.get(rank, ("var(--wc-turquoise)", "#000"))

                st.markdown(f'''
                <div class="wc-card-flat" style="padding:1rem 1.25rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:1rem;">
                    <div style="min-width:2rem; text-align:center;">
                        <span style="background:{badge_bg}; color:{badge_fg}; font-weight:700;
                            font-size:0.85rem; padding:0.3rem 0.55rem; border-radius:6px;">{rank}</span>
                    </div>
                    <div style="font-size:1.8rem;">{flag_t}</div>
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:1.05rem;">{team}</div>
                        <div style="display:flex; align-items:center; gap:0.4rem; margin-top:0.3rem;">
                            <span class="wc-badge" style="background:rgba(255,255,255,0.05); color:var(--text-color); font-size:0.75rem; padding:0.2rem 0.5rem; border-radius:4px;">
                                FIFA Rank: <strong>{actual}</strong>
                            </span>
                            <span class="wc-badge" style="background:rgba(255,255,255,0.05); color:var(--text-color); font-size:0.75rem; padding:0.2rem 0.5rem; border-radius:4px;">
                                Implied: <strong>{imp}</strong> ({rank_delta_str})
                            </span>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.4rem; font-weight:700; color:#7289da;">{poly:.1f}%</div>
                        <div style="font-size:0.7rem; color:#7289da; margin-top:0.15rem;">Polymarket</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
    elif view_mode == "💰 Value Bets":
        render_info_box(
            "<strong>What is Expected Value (EV)?</strong> It represents the expected monetary return on a hypothetical $100 bet "
            "if we assume our simulation's win probabilities are completely accurate compared to Polymarket's odds. "
            "You can buy <strong>YES</strong> if our model thinks a team is undervalued, or buy <strong>NO</strong> if they are overvalued."
            "<br><br><span style='color:var(--wc-primary);'><i class='fas fa-info-circle'></i> <strong>Disclaimer:</strong> "
            "This is a theoretical exercise based on a simulation model, not financial advice.</span>"
        )
        
        champions = get_champion_probs(limit=100)
        if not poly_odds:
            st.info("Polymarket odds are currently unavailable.")
        else:
            ev_data = []
            
            # Focus on the top 12 Polymarket favorites to keep the list relevant
            top_poly_teams = sorted(poly_odds.items(), key=lambda x: x[1].get("yes", 0), reverse=True)[:12]
            
            for team, probs in top_poly_teams:
                poly_prob_yes = probs.get("yes", 0)
                poly_prob_no = probs.get("no", 0)
                
                sim_row = champions[champions["team"] == team]
                sim_prob = sim_row["probability"].values[0] if not sim_row.empty else 0.0
                
                if poly_prob_yes > 0:
                    implied_decimal_yes = 100.0 / poly_prob_yes
                    expected_return_yes = (sim_prob / 100.0) * implied_decimal_yes * 100.0
                    ev_yes = expected_return_yes - 100.0
                    
                    ev_data.append({
                        "team": team,
                        "type": "YES",
                        "poly_prob": poly_prob_yes,
                        "sim_prob": sim_prob,
                        "ev": ev_yes
                    })
                
                if poly_prob_no > 0:
                    sim_prob_no = 100.0 - sim_prob
                    implied_decimal_no = 100.0 / poly_prob_no
                    expected_return_no = (sim_prob_no / 100.0) * implied_decimal_no * 100.0
                    ev_no = expected_return_no - 100.0
                    
                    ev_data.append({
                        "team": team,
                        "type": "NO",
                        "poly_prob": poly_prob_no,
                        "sim_prob": sim_prob_no,
                        "ev": ev_no
                    })
            
            # Sort by EV descending to highlight best value bets
            ev_data.sort(key=lambda x: x["ev"], reverse=True)
            
            # Show top 10 value bets across both types
            for idx, data in enumerate(ev_data[:10]):
                team = data["team"]
                b_type = data["type"]
                poly_prob = data["poly_prob"]
                sim_prob = data["sim_prob"]
                ev = data["ev"]
                
                flag_t = get_flag(team)
                
                ev_color = "#22C55E" if ev > 0 else "#EF4444" if ev < 0 else "var(--wc-secondary)"
                ev_sign = "+" if ev > 0 else ""
                
                # Green subtle background for positive EV
                ev_bg = "rgba(34, 197, 94, 0.08)" if ev > 0 else "var(--card-bg)"
                ev_border = "1px solid rgba(34, 197, 94, 0.3)" if ev > 0 else "1px solid rgba(255,255,255,0.05)"
                
                type_color = "var(--wc-primary)" if b_type == "YES" else "var(--wc-magenta)"
                type_bg_span = "rgba(0, 180, 216, 0.15)" if b_type == "YES" else "rgba(230, 62, 109, 0.15)"
                
                st.markdown(f'''
                <div class="wc-card-flat" style="padding:1rem 1.25rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:1rem; background:{ev_bg}; border:{ev_border};">
                    <div style="font-size:1.8rem; min-width:2.5rem; text-align:center;">{flag_t}</div>
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:1.05rem;">
                            {team} <span style="font-size:0.75rem; background:{type_bg_span}; color:{type_color}; padding:0.15rem 0.4rem; border-radius:4px; margin-left:0.5rem; vertical-align:middle; font-weight:800;">BUY {b_type}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:0.4rem; margin-top:0.3rem;">
                            <span class="wc-badge" style="background:rgba(255,255,255,0.05); color:var(--text-color); font-size:0.75rem; padding:0.2rem 0.5rem; border-radius:4px;">
                                Model {b_type}: <strong>{sim_prob:.1f}%</strong>
                            </span>
                            <span class="wc-badge" style="background:rgba(114,137,218,0.15); color:#7289da; font-size:0.75rem; padding:0.2rem 0.5rem; border-radius:4px;">
                                Polymarket {b_type}: <strong>{poly_prob:.1f}%</strong>
                            </span>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.4rem; font-weight:700; color:{ev_color};">{ev_sign}${ev:.2f}</div>
                        <div style="font-size:0.7rem; color:{ev_color}; opacity:0.8; margin-top:0.15rem;">Expected Value (per $100)</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
                
    else:
        champions = get_champion_probs(limit=10)
        for idx, row in champions.iterrows():
            team = row["team"]
            sim_prob = row["probability"]
            flag = get_flag(team)

            # Polymarket odds lookup
            poly_prob = poly_odds.get(team, {}).get("yes") if poly_odds else None
            poly_html = ""
            if poly_prob is not None:
                diff = sim_prob - poly_prob
                diff_color = "#22C55E" if diff > 0 else "#EF4444" if diff < 0 else "var(--wc-secondary)"
                diff_sign = "+" if diff > 0 else ""
                poly_html = (
                    f'<div style="display:flex; align-items:center; gap:0.4rem; margin-top:0.3rem;">'
                    f'<span class="wc-badge" style="background:rgba(114,137,218,0.15); color:#7289da; '
                    f'font-size:0.75rem; padding:0.2rem 0.5rem; border-radius:4px; font-weight:600;">'
                    f'Polymarket {poly_prob:.1f}%</span>'
                    f'<span style="font-size:0.75rem; color:{diff_color}; font-weight:600;">'
                    f'({diff_sign}{diff:.1f}%)</span>'
                    f'</div>'
                )
            else:
                poly_html = (
                    '<div style="margin-top:0.3rem;">'
                    '<span style="font-size:0.75rem; color:var(--wc-secondary); font-style:italic;">'
                    'Polymarket: n/a</span></div>'
                )

            # Rank badge
            rank = idx + 1
            rank_colors = {
                1: ("var(--wc-gold)", "#000"),
                2: ("#C0C0C0", "#000"),
                3: ("#CD7F32", "#fff"),
            }
            badge_bg, badge_fg = rank_colors.get(rank, ("var(--wc-turquoise)", "#000"))

            st.markdown(f'''
            <div class="wc-card-flat" style="padding:1rem 1.25rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:1rem;">
                <div style="min-width:2rem; text-align:center;">
                    <span style="background:{badge_bg}; color:{badge_fg}; font-weight:700;
                        font-size:0.85rem; padding:0.3rem 0.55rem; border-radius:6px;">{rank}</span>
                </div>
                <div style="font-size:1.8rem;">{flag}</div>
                <div style="flex:1;">
                    <div style="font-weight:700; font-size:1.05rem;">{team}</div>
                    {poly_html}
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.4rem; font-weight:700; color:var(--wc-turquoise);">{sim_prob:.1f}%</div>
                    <div style="font-size:0.7rem; color:var(--wc-secondary); margin-top:0.15rem;">Simulation</div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

    # Attribution / Link
    st.markdown("<br>", unsafe_allow_html=True)
    if poly_odds:
        st.caption(
            "Polymarket odds are fetched live from the "
            "[2026 FIFA World Cup Winner](https://polymarket.com/event/2026-fifa-world-cup-winner-595) "
            "prediction market and cached for 8 hours."
        )
    else:
        st.caption(
            "⚠️ Could not load Polymarket odds. Showing simulation data only. "
            "[View on Polymarket →](https://polymarket.com/event/2026-fifa-world-cup-winner-595)"
        )

# --- Head-to-Head view ---
elif selected_stage == "HEAD_TO_HEAD":
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
        f'<div class="wc-section-sub">Top 12 Most Likely {display_name} Matchups</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Showing the 12 most frequently occurring matchups across all 100,000 simulations."
    )

    matchups = get_stage_matchups(selected_stage, limit=12)

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
