"""
Reusable UI components for the Simulator page.
"""
import math
import streamlit as st
from ui.flags import get_flag

def is_stat_sig_prop(user_prob, base_prob, num_sims):
    """Check statistical significance for proportions (percentages 0-100)."""
    if not num_sims:
        return True
    p_hat = user_prob / 100.0
    p_0 = base_prob / 100.0
    if p_0 == 0 or p_0 == 1:
        return p_hat != p_0
        
    se = math.sqrt((p_0 * (1 - p_0)) / num_sims)
    if se == 0:
        return False
        
    z = (p_hat - p_0) / se
    return abs(z) > 1.96


def render_shift_badge(shift: float, is_sig: bool = True) -> str:
    """Return HTML string for a probability shift badge.

    Turquoise for positive, magenta for negative, muted for neutral.
    """
    if not is_sig:
        return f'<span class="wc-shift-neutral" style="opacity: 0.6; font-size: 0.85em;" title="Not statistically significant">{shift:+.1f}%</span>'

    if shift > 0.05:
        css = "wc-shift-positive"
        text = f"+{shift:.1f}%"
    elif shift < -0.05:
        css = "wc-shift-negative"
        text = f"{shift:.1f}%"
    else:
        css = "wc-shift-neutral"
        text = f"{shift:+.1f}%"
    return f'<span class="{css}" style="font-weight:bold;">{text}</span>'


def render_score_shift_badge(shift: float, is_sig: bool = True) -> str:
    """Return HTML string for a non-percentage float shift (e.g. for avg score)."""
    if not is_sig:
        return f'<span class="wc-shift-neutral" style="opacity: 0.6; font-size: 0.85em;" title="Not statistically significant">{shift:+.2f}</span>'

    if shift > 0.005:
        css = "wc-shift-positive"
        text = f"+{shift:.2f}"
    elif shift < -0.005:
        css = "wc-shift-negative"
        text = f"{shift:.2f}"
    else:
        css = "wc-shift-neutral"
        text = f"{shift:+.2f}"
    return f'<span class="{css}" style="font-weight:bold;">{text}</span>'


def render_podium_with_shifts(position: str, team: str, user_prob: float,
                              base_prob: float, shift: float, css_class: str):
    """Render a podium card showing user probability with shift from baseline."""
    flag = get_flag(team)
    shift_html = render_shift_badge(shift)

    st.markdown(f"""
    <div class="{css_class}">
        <div class="wc-podium-position">{position}</div>
        <div class="wc-podium-flag">{flag}</div>
        <div class="wc-podium-team">{team}</div>
        <div class="wc-podium-prob">{user_prob:.1f}%</div>
        <div style="font-size:0.8rem; margin-top:0.25rem; color:var(--wc-secondary);">
            Baseline: {base_prob:.1f}% &nbsp;{shift_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_champion_shifts_table(podium_data: list[dict]):
    """Render a table of championship probability shifts.

    Args:
        podium_data: list of dicts with keys: team, user_prob, base_prob, shift
    """
    html = '<div class="wc-card-flat" style="padding:0.75rem;">'
    html += '<table class="wc-sim-results-table"><thead><tr>'
    html += '<th>Team</th><th>Your Sim</th><th>Baseline</th><th>Shift</th>'
    html += '</tr></thead><tbody>'

    for d in podium_data:
        flag = get_flag(d["team"])
        shift_html = render_shift_badge(d["shift"])
        html += '<tr>'
        html += f'<td>{flag} {d["team"]}</td>'
        html += f'<td><strong>{d["user_prob"]:.1f}%</strong></td>'
        html += f'<td>{d["base_prob"]:.1f}%</td>'
        html += f'<td>{shift_html}</td>'
        html += '</tr>'

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)


def render_sim_group_table(user_standings: list[dict], baseline_order: list[str],
                           group_name: str, is_sig_dict: dict = None):
    """Render a compact group table from user simulation with position shifts.

    Args:
        user_standings: list of dicts with position, team, probability, advanced
        baseline_order: list of team names in baseline finishing order
        group_name: Group letter
    """
    prob = user_standings[0]["probability"] if user_standings else 0
    header = (
        f'<div class="wc-section-sub" style="font-size:0.95rem;">'
        f'Group {group_name}'
        f' <span class="wc-badge wc-badge-turquoise">{prob:.0f}%</span>'
        f'</div>'
    )

    html = '<div class="wc-card-flat" style="padding:0.4rem 0.5rem;">'
    html += '<table class="wc-group-table"><thead><tr>'
    html += '<th>#</th><th>Team</th><th>Shift</th>'
    html += '</tr></thead><tbody>'

    baseline_positions = {team: i + 1 for i, team in enumerate(baseline_order)}

    for r in user_standings:
        team = r["team"]
        flag = get_flag(team)
        row_class = "advanced" if r.get("advanced") else "eliminated"
        user_pos = r["position"]
        base_pos = baseline_positions.get(team, user_pos)
        pos_diff = base_pos - user_pos  # positive = moved up

        is_sig = is_sig_dict.get(team, False) if is_sig_dict else True
        if pos_diff == 0:
            shift_html = '<span class="wc-shift-neutral">-</span>'
        elif not is_sig:
            shift_html = f'<span class="wc-shift-neutral" style="opacity: 0.6; font-size: 0.85em;" title="Not statistically significant">{pos_diff:+d}</span>'
        elif pos_diff > 0:
            shift_html = f'<span class="wc-shift-positive" style="font-weight:bold;">+{pos_diff}</span>'
        else:
            shift_html = f'<span class="wc-shift-negative" style="font-weight:bold;">{pos_diff}</span>'

        html += f'<tr class="{row_class}">'
        html += f'<td>{user_pos}</td>'
        html += f'<td>{flag} {team}</td>'
        html += f'<td>{shift_html}</td>'
        html += '</tr>'

    html += '</tbody></table></div>'

    st.markdown(header, unsafe_allow_html=True)
    st.markdown(html, unsafe_allow_html=True)


def render_team_progression_table(team: str, user_stages, baseline_stages, num_sims: int = None):
    """Render a stage-by-stage comparison table for a team.

    Args:
        team: Team name
        user_stages: DataFrame with stage, probability columns (user sims)
        baseline_stages: DataFrame with stage, probability columns (100k baseline)
        num_sims: Optional number of sims to compute statistical significance.
    """
    baseline_dict = {}
    for _, row in baseline_stages.iterrows():
        baseline_dict[row["stage"]] = row["probability"]

    stage_order = [
        ("GROUP_STAGE", "Group Stage"),
        ("ROUND_OF_32", "Round of 32"),
        ("ROUND_OF_16", "Round of 16"),
        ("QUARTER_FINALS", "Quarter-Finals"),
        ("SEMI_FINALS", "Semi-Finals"),
        ("FINAL", "Final"),
        ("CHAMPION", "Champion"),
    ]

    html = '<table class="wc-sim-results-table"><thead><tr>'
    html += '<th>Stage</th><th>Your Sim</th><th>Baseline</th><th>Shift</th>'
    html += '</tr></thead><tbody>'

    for stage_key, display in stage_order:
        user_row = user_stages[user_stages["stage"] == stage_key]
        u_prob = float(user_row["probability"].iloc[0]) if not user_row.empty else 0.0
        b_prob = baseline_dict.get(stage_key, 0.0)
        s = u_prob - b_prob
        
        is_sig = False if stage_key == "GROUP_STAGE" else is_stat_sig_prop(u_prob, b_prob, num_sims)
        shift_html = render_shift_badge(s, is_sig)

        html += '<tr>'
        html += f'<td>{display}</td>'
        html += f'<td><strong>{u_prob:.1f}%</strong></td>'
        html += f'<td>{b_prob:.1f}%</td>'
        html += f'<td>{shift_html}</td>'
        html += '</tr>'

    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)
