"""
Bracket and pipeline visualization components.
"""
import streamlit as st
import pandas as pd
from ui.flags import get_flag
from config import STAGE_DISPLAY_NAMES


def render_mini_bracket(bracket_df: pd.DataFrame):
    """Render a compact mini-bracket overview of the knockout stage.

    Args:
        bracket_df: DataFrame with columns: match_number, stage, city, most_likely_winner, prob
    """
    stages = ["ROUND_OF_32", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
    stage_matches = {s: bracket_df[bracket_df["stage"] == s].sort_values("match_number") for s in stages}

    # Start container
    st.markdown('<div class="wc-bracket-container" style="display:flex; gap:1rem; align-items:flex-start;">', unsafe_allow_html=True)

    for stage in stages:
        matches = stage_matches.get(stage, pd.DataFrame())
        if matches.empty:
            continue
        display_name = STAGE_DISPLAY_NAMES.get(stage, stage)

        # Render round title
        st.markdown(f'<div class="wc-bracket-round"><div class="wc-bracket-round-title">{display_name}</div>', unsafe_allow_html=True)

        # Render each match separately
        for _, row in matches.iterrows():
            winner = row["most_likely_winner"]
            flag = get_flag(winner)
            prob = row["prob"]
            st.markdown(f"""
            <div class="wc-bracket-match">
                <div class="winner">{flag} {winner}</div>
                <div class="prob">{prob:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        # Close round div
        st.markdown("</div>", unsafe_allow_html=True)

    # Close container
    st.markdown("</div>", unsafe_allow_html=True)


def render_team_pipeline(stage_probs: list[dict]):
    """Render a horizontal tournament path pipeline for a team.

    Args:
        stage_probs: List of dicts with keys: stage, display_name, probability, reached
            Ordered from Group Stage to Final. 'reached' is True if the team
            reaches that stage with >0% probability.
    """
    html = '<div class="wc-pipeline">'
    for i, sp in enumerate(stage_probs):
        if i > 0:
            conn_class = "wc-pipeline-connector" if sp["reached"] else "wc-pipeline-connector inactive"
            html += f'<div class="{conn_class}"></div>'

        if not sp["reached"]:
            node_class = "wc-pipeline-node inactive"
        else:
            node_class = "wc-pipeline-node active"

        html += f"""
        <div class="{node_class}">
            <div class="stage-name">{sp['display_name']}</div>
            <div class="stage-prob">{sp['probability']:.1f}%</div>
        </div>
        """

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_team_path_card(path_description: str, probability: float, is_top: bool = False):
    """Render a single team path as a card.

    Args:
        path_description: HTML string describing the path
        probability: Probability as percentage
        is_top: Whether this is the most likely path
    """
    border_color = "var(--wc-turquoise)" if is_top else "#E5E7EB"
    st.markdown(f"""
    <div class="wc-card-flat" style="border-left: 4px solid {border_color}; padding-left:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:0.9rem;">{path_description}</div>
            <div class="wc-badge wc-badge-turquoise" style="font-size:0.85rem;">{probability:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
