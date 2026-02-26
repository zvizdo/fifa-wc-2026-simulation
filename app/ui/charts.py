"""
Plotly chart builders for the FIFA WC 2026 app.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import PRIMARY_TURQUOISE, MAGENTA, GOLD, DARK_BG, COUNTRY_COLORS, CITY_COORDS, CITY_STADIUMS


def create_outcome_bar_chart(df: pd.DataFrame, team_name: str) -> go.Figure:
    """Create a horizontal bar chart of outcome probabilities for a team.

    Args:
        df: DataFrame with columns: outcome, probability
        team_name: Team name for the title
    """
    fig = px.bar(
        df,
        x="probability",
        y="outcome",
        orientation="h",
        text="probability",
        color_discrete_sequence=[PRIMARY_TURQUOISE],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )
    fig.update_layout(
        title=None,
        xaxis_title="Probability (%)",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=40, t=10, b=30),
        height=max(250, len(df) * 40),
        font=dict(size=12, color="#374151"), # Darker text for readability
        xaxis=dict(
            showgrid=True, 
            gridcolor="#E5E7EB",
            title_font=dict(size=13, color="#111827", weight="bold"),
            tickfont=dict(color="#374151")
        ),
        yaxis=dict(
             autorange="reversed",
             tickfont=dict(color="#111827", weight="bold") # Darker, bold labels
        ),
    )
    return fig


def create_city_map(city_overview_df: pd.DataFrame) -> go.Figure:
    """Create a scatter geo map of all 16 host cities.

    Args:
        city_overview_df: DataFrame with columns: city, country, num_knockout_matches, stages
    """
    # Enrich the dataframe with coords and display info
    rows = []
    for _, row in city_overview_df.iterrows():
        city = row["city"]
        coords = CITY_COORDS.get(city, {})
        stadium_info = CITY_STADIUMS.get(city, ("", 0))
        knockout = int(row.get("num_knockout_matches", 0) or 0)
        rows.append({
            "city": city,
            "country": row["country"],
            "lat": coords.get("lat", 0),
            "lon": coords.get("lon", 0),
            "size": max(8, knockout * 4 + 8),
            "hover": (
                f"<b>{city}</b><br>"
                f"{stadium_info[0]}<br>"
                f"Capacity: {stadium_info[1]:,}<br>"
                f"Knockout matches: {knockout}<br>"
                f"Stages: {row.get('stages', '')}"
            ),
        })

    fig = go.Figure()
    for country, color in COUNTRY_COLORS.items():
        country_rows = [r for r in rows if r["country"] == country]
        if not country_rows:
            continue
        fig.add_trace(go.Scattergeo(
            lat=[r["lat"] for r in country_rows],
            lon=[r["lon"] for r in country_rows],
            text=[r["city"] for r in country_rows],
            textposition="top center",
            mode="markers+text",
            marker=dict(
                size=[r["size"] for r in country_rows],
                color=color,
                line=dict(width=1, color="white"),
                opacity=0.85,
            ),
            hovertext=[r["hover"] for r in country_rows],
            hoverinfo="text",
            name=country,
        ))

    fig.update_geos(
        scope="north america",
        showland=True,
        landcolor="#F0F4F8",
        showocean=True,
        oceancolor="#E0F7FA",
        showlakes=True,
        lakecolor="#E0F7FA",
        showcountries=True,
        countrycolor="#D1D5DB",
        showsubunits=True,
        subunitcolor="#E5E7EB",
        center=dict(lat=37, lon=-98),
        projection_scale=2.5,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    return fig


def create_opponent_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart showing opponents and win rates.

    Args:
        df: DataFrame with columns: opponent, total, wins, losses, matchup_pct
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["opponent"],
        x=df["wins"],
        name="Wins",
        orientation="h",
        marker_color=PRIMARY_TURQUOISE,
    ))
    fig.add_trace(go.Bar(
        y=df["opponent"],
        x=df["losses"],
        name="Losses",
        orientation="h",
        marker_color=MAGENTA,
    ))

    fig.update_layout(
        barmode="stack",
        title=None,
        xaxis_title="Matches",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=20, t=10, b=30),
        height=max(200, len(df) * 35),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=12, color="#374151"), # Darker text
        xaxis=dict(
            title_font=dict(size=13, color="#111827", weight="bold"),
            tickfont=dict(color="#374151")
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(color="#111827", weight="bold")
        ),
    )
    return fig
