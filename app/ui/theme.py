"""
FIFA World Cup 2026 themed CSS injection for Streamlit.
"""
import streamlit as st


def inject_css():
    """Inject the FIFA 2026 branded CSS into the Streamlit app."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
<style>
/* ===== Force light mode ===== */
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
.main,
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    color: #0A1628 !important;
}

/* ===== Root variables ===== */
:root {
    --wc-turquoise: #00B4D8;
    --wc-magenta: #E63E6D;
    --wc-gold: #FFB703;
    --wc-dark: #0A1628;
    --wc-light: #F0F4F8;
    --wc-card-bg: #FFFFFF;
    --wc-secondary: #6B7280;
    --wc-turquoise-light: #E0F7FA;
    --wc-magenta-light: #FCE4EC;
    --wc-gold-light: #FFF8E1;
}

/* ===== Hide default Streamlit elements for cleaner look ===== */
#MainMenu {visibility: hidden;}
header[data-testid="stHeader"],
[data-testid="stToolbar"],
.stAppToolbar {
    background: transparent !important;
    pointer-events: none !important; /* Allow clicks to pass through to custom nav */
}
/* Re-enable pointer events for the important header buttons (Menu & Deploy) */
button[data-testid="stHeaderMenu"], 
.stDeployButton,
[data-testid="stToolbar"] button,
[data-testid="stAppDeployButton"] {
    pointer-events: auto !important;
}

/* ===== Reduce default Streamlit top padding & divider spacing ===== */
[data-testid="stMainBlockContainer"] {
    padding-top: 16px !important;
}
hr {
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}

/* ===== Page link nav buttons (global baseline — used outside the top nav) ===== */
a[data-testid="stPageLink-NavLink"] {
    background: #FFFFFF !important;
    color: var(--wc-dark) !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.25rem !important;
    text-decoration: none !important;
    font-weight: 600 !important;
    border: 1.5px solid #E5E7EB !important;
    border-left: 3px solid var(--wc-turquoise) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06) !important;
    transition: all 0.2s ease !important;
}
a[data-testid="stPageLink-NavLink"]:hover {
    border-color: var(--wc-turquoise) !important;
    border-left: 3px solid var(--wc-turquoise) !important;
    box-shadow: 0 2px 8px rgba(0, 180, 216, 0.15) !important;
    transform: translateY(-1px);
}
a[data-testid="stPageLink-NavLink"] p,
a[data-testid="stPageLink-NavLink"] span {
    color: var(--wc-dark) !important;
    font-weight: 600 !important;
}

/* ===== Desktop nav bar ===== */
/* Native Streamlit page links styled as a horizontal navbar */
.st-key-desktop_nav {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    background: linear-gradient(135deg, var(--wc-dark) 0%, #162236 100%) !important;
    border-radius: 14px !important;
    padding: 0 1rem !important;
    height: 54px !important;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.22) !important;
    gap: 0.25rem !important;
    width: 100% !important;
    position: relative !important;
    z-index: 999999 !important;
}

/* Ensure brand text is pushed to the left by letting it grow */
.st-key-desktop_nav .stElementContainer:first-child {
    margin-right: auto !important;
    flex-grow: 1 !important;
    width: auto !important;
    margin: 0 !important;
}

/* Zero out Streamlit's default markdown margins to center brand text */
.st-key-desktop_nav div.stMarkdown,
.st-key-desktop_nav [data-testid="stMarkdownContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
}

/* Base element container sizing for children */
.st-key-desktop_nav .stElementContainer,
.st-key-desktop_nav div[data-testid="stPageLink"] {
    width: auto !important;
    height: 40px !important; /* Fit comfortably within the 54px navbar */
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
}

.wc-nav-brand {
    color: var(--wc-gold) !important;
    font-weight: 800 !important;
    font-size: 1rem !important;
    letter-spacing: 0.4px !important;
    white-space: nowrap !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
}

/* Clean up Desktop Page Links to look like nav buttons */
.st-key-desktop_nav a[data-testid="stPageLink-NavLink"] {
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: rgba(240, 244, 248, 0.82) !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    letter-spacing: 0.2px !important;
    padding: 0 1.25rem !important;
    border-radius: 10px !important;
    transition: background 0.2s ease, color 0.2s ease !important;
    white-space: nowrap !important;
}

.st-key-desktop_nav a[data-testid="stPageLink-NavLink"]:hover {
    background: rgba(0, 180, 216, 0.15) !important;
    color: var(--wc-turquoise) !important;
    border: none !important;
    transform: none !important;
    box-shadow: none !important;
}

/* Ensure hit-testing ALWAYS falls to the parent a tag, preventing the inner text from blocking hover overrides */
.st-key-desktop_nav a[data-testid="stPageLink-NavLink"] * {
    pointer-events: none !important;
}

/* Reset inner p/span in desktop links */
.st-key-desktop_nav a[data-testid="stPageLink-NavLink"] p,
.st-key-desktop_nav a[data-testid="stPageLink-NavLink"] span {
    color: inherit !important;
}

/* ===== Mobile nav bar ===== */
.st-key-mobile_nav [data-testid="stExpander"] {
    background: linear-gradient(135deg, var(--wc-dark) 0%, #162236 100%) !important;
    border: none !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.22) !important;
    overflow: hidden !important;
}
.st-key-mobile_nav summary {
    padding: 0.65rem 1.25rem !important;
}
.st-key-mobile_nav summary p,
.st-key-mobile_nav summary span {
    color: var(--wc-gold) !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
}
.st-key-mobile_nav [data-testid="stIconMaterial"] {
    color: var(--wc-turquoise) !important;
}
.st-key-mobile_nav [data-testid="stExpanderDetails"] {
    padding: 0.25rem 0.75rem 0.75rem !important;
}
.st-key-mobile_nav a[data-testid="stPageLink-NavLink"] {
    background: rgba(255, 255, 255, 0.04) !important;
    border-color: rgba(255, 255, 255, 0.08) !important;
    border-left-color: var(--wc-turquoise) !important;
    box-shadow: none !important;
}
.st-key-mobile_nav a[data-testid="stPageLink-NavLink"] p,
.st-key-mobile_nav a[data-testid="stPageLink-NavLink"] span {
    color: rgba(240, 244, 248, 0.85) !important;
}
.st-key-mobile_nav a[data-testid="stPageLink-NavLink"]:hover {
    background: rgba(0, 180, 216, 0.15) !important;
    border-left-color: var(--wc-turquoise) !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ===== Pills / segmented control ===== */
button[data-testid="stBaseButton-pillsActive"] {
    background-color: var(--wc-turquoise) !important;
    color: #FFFFFF !important;
    border-color: var(--wc-turquoise) !important;
}
button[data-testid="stBaseButton-pillsActive"] p {
    color: #FFFFFF !important;
}
button[data-testid="stBaseButton-pills"] {
    background-color: var(--wc-card-bg) !important;
    color: var(--wc-dark) !important;
    border-color: #D1D5DB !important;
}
button[data-testid="stBaseButton-pills"] p {
    color: var(--wc-dark) !important;
}
button[data-testid="stBaseButton-pills"]:hover {
    border-color: var(--wc-turquoise) !important;
    color: var(--wc-turquoise) !important;
}
button[data-testid="stBaseButton-pills"]:hover p {
    color: var(--wc-turquoise) !important;
}

/* ===== Radio Buttons ===== */
[data-testid="stRadio"] label,
[data-testid="stRadio"] p,
[data-testid="stRadio"] span {
    color: var(--wc-dark) !important;
}
[data-testid="stRadio"] div[role="radiogroup"] {
    background-color: var(--wc-card-bg) !important;
    padding: 0.2rem 0.5rem;
    border-radius: 8px;
}

/* ===== Navigation visibility ===== */

/* Desktop-first: hide mobile nav by default */
.st-key-mobile_nav { display: none !important; }

/* ===== Streamlit Tabs ===== */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--wc-turquoise) !important;
    border-bottom-color: var(--wc-turquoise) !important;
}
button[data-baseweb="tab"]:hover {
    color: var(--wc-turquoise) !important;
    background-color: transparent !important;
}
button[data-baseweb="tab"]:focus {
    background-color: transparent !important;
}

/* ===== Card styles ===== */
.wc-card {
    border-radius: 12px;
    padding: 1.5rem;
    background: var(--wc-card-bg);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    border: 1px solid #E5E7EB;
    margin-bottom: 1rem;
    transition: transform 0.2s, box-shadow 0.2s;
}

.wc-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.wc-card-flat {
    border-radius: 12px;
    padding: 1.25rem;
    background: var(--wc-card-bg);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    border: 1px solid #E5E7EB;
    margin-bottom: 0.75rem;
    overflow-x: auto;
}

/* ===== Podium cards ===== */
.wc-podium-gold {
    background: linear-gradient(135deg, #FFB703 0%, #FFC940 100%);
    border-radius: 16px;
    padding: 2rem 1.5rem;
    text-align: center;
    color: var(--wc-dark);
    box-shadow: 0 4px 20px rgba(255, 183, 3, 0.3);
    border: none;
}

.wc-podium-silver {
    background: linear-gradient(135deg, #C0C0C0 0%, #E8E8E8 100%);
    border-radius: 16px;
    padding: 2rem 1.5rem;
    text-align: center;
    color: var(--wc-dark);
    box-shadow: 0 4px 20px rgba(192, 192, 192, 0.3);
    border: none;
}

.wc-podium-bronze {
    background: linear-gradient(135deg, #CD7F32 0%, #D4943A 100%);
    border-radius: 16px;
    padding: 2rem 1.5rem;
    text-align: center;
    color: var(--wc-dark);
    box-shadow: 0 4px 20px rgba(205, 127, 50, 0.3);
    border: none;
}

.wc-podium-position {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.25rem;
    opacity: 0.8;
}

.wc-podium-flag {
    font-size: 3rem;
    margin-bottom: 0.25rem;
}

.wc-podium-team {
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}

.wc-podium-prob {
    font-size: 2rem;
    font-weight: 800;
}

.wc-podium-secondary {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: rgba(0,0,0,0.04);
    border-radius: 8px;
    margin-top: 0.5rem;
    font-size: 0.9rem;
}

.wc-podium-secondary .team-name {
    flex: 1;
    font-weight: 500;
}

.wc-podium-secondary .prob {
    font-weight: 700;
    color: var(--wc-turquoise);
}

/* ===== Match card ===== */
.wc-match-card {
    border-radius: 12px;
    padding: 1.25rem;
    background: var(--wc-card-bg);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    border: 1px solid #E5E7EB;
    margin-bottom: 0.75rem;
}

.wc-match-teams {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.5rem;
}

.wc-match-team {
    font-size: 1.1rem;
    font-weight: 600;
    text-align: center;
    flex: 1;
}

.wc-match-vs {
    color: var(--wc-secondary);
    font-size: 0.85rem;
    font-weight: 500;
}

.wc-match-prob {
    text-align: center;
    font-size: 0.9rem;
    color: var(--wc-secondary);
}

.wc-match-prob strong {
    color: var(--wc-turquoise);
    font-size: 1.1rem;
}

/* ===== Probability bar ===== */
.wc-prob-bar-container {
    width: 100%;
    background: #E5E7EB;
    border-radius: 6px;
    overflow: hidden;
    height: 8px;
    margin: 0.5rem 0;
}

.wc-prob-bar {
    height: 100%;
    border-radius: 6px;
    background: linear-gradient(90deg, var(--wc-turquoise), #0096C7);
    transition: width 0.5s ease;
}

.wc-prob-bar-gold {
    background: linear-gradient(90deg, var(--wc-gold), #FFC940);
}

.wc-prob-bar-magenta {
    background: linear-gradient(90deg, var(--wc-magenta), #FF6B8A);
}

/* ===== Pipeline (team path) ===== */
.wc-pipeline {
    display: flex;
    align-items: center;
    overflow-x: auto;
    padding: 1rem 0;
    gap: 0;
}

.wc-pipeline-node {
    padding: 0.6rem 1rem;
    border-radius: 10px;
    border: 2px solid var(--wc-turquoise);
    background: var(--wc-turquoise-light);
    text-align: center;
    min-width: 100px;
    white-space: nowrap;
    flex-shrink: 0;
}

.wc-pipeline-node.active {
    background: var(--wc-turquoise);
    color: white;
    font-weight: 600;
}

.wc-pipeline-node.exit-node {
    border-color: var(--wc-magenta);
    background: var(--wc-magenta-light);
}

.wc-pipeline-node.exit-node.active {
    background: var(--wc-magenta);
    color: white;
}

.wc-pipeline-node.inactive {
    border-color: #D1D5DB;
    background: #F3F4F6;
    color: #9CA3AF;
}

.wc-pipeline-node .stage-name {
    font-size: 0.8rem;
    font-weight: 600;
}

.wc-pipeline-node .stage-prob {
    font-size: 0.75rem;
    margin-top: 2px;
}

.wc-pipeline-connector {
    width: 30px;
    height: 2px;
    background: var(--wc-turquoise);
    flex-shrink: 0;
}

.wc-pipeline-connector.inactive {
    background: #D1D5DB;
}

/* ===== Section headers ===== */
.wc-section-header {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--wc-dark);
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 3px solid var(--wc-turquoise);
}

.wc-section-sub {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--wc-dark);
    margin-bottom: 0.5rem;
}

/* ===== Hero section ===== */
.wc-hero {
    text-align: center;
    padding: 3rem 1rem 2rem;
    margin-bottom: 2rem;
    background: linear-gradient(135deg, var(--wc-dark) 0%, #1A2940 100%);
    border-radius: 20px;
    color: var(--wc-light);
}

.wc-hero h1 {
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
    background: linear-gradient(90deg, var(--wc-turquoise), var(--wc-gold));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.wc-hero .subtitle {
    font-size: 1.15rem;
    color: rgba(240, 244, 248, 0.8);
    max-width: 600px;
    margin: 0 auto;
}

/* ===== Stat metrics row ===== */
.wc-stat-box {
    text-align: center;
    padding: 1rem;
    background: var(--wc-card-bg);
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    border: 1px solid #E5E7EB;
}

.wc-stat-box .value {
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--wc-turquoise);
}

.wc-stat-box .label {
    font-size: 0.85rem;
    color: var(--wc-secondary);
    font-weight: 500;
}

/* ===== CTA cards ===== */
.wc-cta-card {
    border-radius: 14px;
    padding: 1.5rem;
    text-align: center;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    border: 2px solid transparent;
}

.wc-cta-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
}

.wc-cta-turquoise {
    background: linear-gradient(135deg, #E0F7FA, #B2EBF2);
    border-color: var(--wc-turquoise);
}

.wc-cta-magenta {
    background: linear-gradient(135deg, #FCE4EC, #F8BBD0);
    border-color: var(--wc-magenta);
}

.wc-cta-gold {
    background: linear-gradient(135deg, #FFF8E1, #FFECB3);
    border-color: var(--wc-gold);
}

.wc-cta-card .cta-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

.wc-cta-card .cta-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--wc-dark);
    margin-bottom: 0.25rem;
}

.wc-cta-card .cta-desc {
    font-size: 0.85rem;
    color: var(--wc-secondary);
}

/* ===== Group standings table ===== */
.wc-group-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.75rem;
}

.wc-group-table th {
    padding: 0.3rem 0.35rem;
    text-align: left;
    font-weight: 600;
    color: var(--wc-secondary);
    border-bottom: 2px solid var(--wc-turquoise);
    font-size: 0.7rem;
    text-transform: uppercase;
    white-space: nowrap;
}

.wc-group-table td {
    padding: 0.3rem 0.35rem;
    border-bottom: 1px solid #F3F4F6;
    white-space: nowrap;
}

.wc-group-table tr.advanced td {
    background: rgba(0, 180, 216, 0.06);
}

.wc-group-table tr.eliminated td {
    color: #9CA3AF;
}

/* ===== Bracket mini ===== */
.wc-bracket-container {
    overflow-x: auto;
    padding: 1rem 0;
}

.wc-bracket-round {
    display: inline-flex;
    flex-direction: column;
    gap: 0.5rem;
    vertical-align: top;
    margin-right: 1rem;
}

.wc-bracket-round-title {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--wc-secondary);
    text-align: center;
    margin-bottom: 0.25rem;
}

.wc-bracket-match {
    padding: 0.4rem 0.75rem;
    background: var(--wc-card-bg);
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    font-size: 0.8rem;
    min-width: 120px;
    text-align: center;
}

.wc-bracket-match .winner {
    font-weight: 600;
    color: var(--wc-dark);
}

.wc-bracket-match .prob {
    font-size: 0.7rem;
    color: var(--wc-secondary);
}

/* ===== Misc ===== */
.wc-info-box {
    padding: 1rem 1.25rem;
    background: var(--wc-turquoise-light);
    border-left: 4px solid var(--wc-turquoise);
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: var(--wc-dark);
}

.wc-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}

.wc-badge-turquoise {
    background: var(--wc-turquoise-light);
    color: var(--wc-turquoise);
}

.wc-badge-magenta {
    background: var(--wc-magenta-light);
    color: var(--wc-magenta);
}

.wc-badge-gold {
    background: var(--wc-gold-light);
    color: #B8860B;
}

/* ===== Score display ===== */
.wc-score {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 0.5rem;
    font-size: 1rem;
}

.wc-score .team {
    font-weight: 500;
    min-width: 100px;
}

.wc-score .team.left {
    text-align: right;
}

.wc-score .team.right {
    text-align: left;
}

.wc-score .goals {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--wc-dark);
    min-width: 50px;
    text-align: center;
}

.wc-score .winner-indicator {
    color: var(--wc-turquoise);
}

/* ===== Mobile responsive ===== */
@media (max-width: 768px) {

    /* Switch from desktop nav to mobile hamburger */
    .st-key-desktop_nav { display: none !important; }
    .st-key-mobile_nav { display: block !important; }

    /* --- Hero --- */
    .wc-hero {
        padding: 1.5rem 1rem;
    }

    .wc-hero h1 {
        font-size: 1.6rem;
    }

    .wc-hero .subtitle {
        font-size: 0.9rem;
    }

    /* --- Podium --- */
    .wc-podium-flag {
        font-size: 2rem;
    }
    .wc-podium-team {
        font-size: 1rem;
    }
    .wc-podium-prob {
        font-size: 1.5rem;
    }
    .wc-podium-gold,
    .wc-podium-silver,
    .wc-podium-bronze {
        padding: 1.25rem 1rem;
    }

    /* --- Stat boxes --- */
    .wc-stat-box .value {
        font-size: 1.3rem;
    }
    .wc-stat-box {
        padding: 0.75rem 0.5rem;
    }

    /* --- CTA cards --- */
    .wc-cta-card {
        padding: 1.25rem 1rem;
    }
    .wc-cta-card .cta-icon {
        font-size: 1.5rem;
    }
    .wc-cta-card .cta-title {
        font-size: 1rem;
    }

    /* --- Pipeline (team path) --- */
    .wc-pipeline-node {
        padding: 0.4rem 0.6rem;
        min-width: 70px;
        font-size: 0.75rem;
    }
    .wc-pipeline-connector {
        width: 15px;
    }

    /* --- Reduce Streamlit top padding on mobile --- */
    .block-container {
        padding-top: 0.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* --- Match card --- */
    .wc-match-team {
        font-size: 0.9rem;
    }
}

/* ===== Simulator page ===== */

.wc-sim-changes-summary {
    background: var(--wc-light);
    border-left: 3px solid var(--wc-magenta);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.85rem;
}

.wc-sim-changes-summary .change-item {
    display: inline-block;
    margin-right: 1rem;
    margin-bottom: 0.25rem;
}

.wc-shift-positive { color: var(--wc-turquoise); font-weight: 700; }
.wc-shift-negative { color: var(--wc-magenta); font-weight: 700; }
.wc-shift-neutral  { color: var(--wc-secondary); font-weight: 500; }

.wc-sim-results-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}

.wc-sim-results-table th {
    text-align: left;
    padding: 0.4rem 0.5rem;
    border-bottom: 2px solid var(--wc-turquoise);
    font-size: 0.8rem;
    color: var(--wc-secondary);
}

.wc-sim-results-table td {
    padding: 0.35rem 0.5rem;
    border-bottom: 1px solid #F0F0F0;
}

.wc-sim-results-table tr:hover {
    background: rgba(0, 180, 216, 0.04);
}

/* ===== Buttons ========================================= */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    line-height: 1.5 !important;
    transition: all 0.2s ease !important;
    /* Reset browser specific button styles: */
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
}

/* Primary buttons */
.stButton > button[kind="primary"] {
    background-color: var(--wc-turquoise) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--wc-turquoise) !important;
    box-shadow: 0 4px 12px rgba(0, 180, 216, 0.25) !important;
}

.stButton > button[kind="primary"]:hover {
    background-color: #0096C7 !important;
    border-color: #0096C7 !important;
    box-shadow: 0 6px 16px rgba(0, 180, 216, 0.35) !important;
    color: #FFFFFF !important;
}

/* Secondary buttons */
.stButton > button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: var(--wc-dark) !important;
    border: 1px solid #D1D5DB !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
}

.stButton > button[kind="secondary"]:hover {
    border-color: var(--wc-turquoise) !important;
    color: var(--wc-turquoise) !important;
    background-color: rgba(0, 180, 216, 0.04) !important;
}

/* Force internal paragraphs and spans to inherit button color securely on Brave */
.stButton > button p, 
.stButton > button span {
    color: inherit !important;
}

/* ===== Expanders ========================================= */
[data-testid="stExpander"] {
    border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    background-color: var(--wc-card-bg) !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
    overflow: hidden !important;
    margin-bottom: 0.5rem !important;
}

/* Standard expander styling */
[data-testid="stExpander"] > summary {
    padding: 0.75rem 1rem !important;
    background-color: #F8FAFC !important;
    transition: background-color 0.2s ease !important;
}

[data-testid="stExpander"] > summary:hover {
    background-color: #F1F5F9 !important;
}

/* Force inner details of regular expanders to be consistent */
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    padding: 1rem !important;
    background-color: var(--wc-card-bg) !important;
}

/* Default Expanders (like rank adjustments) - standard text color */
[data-testid="stExpander"] > summary p,
[data-testid="stExpander"] > summary span {
    color: var(--wc-dark) !important;
    font-weight: 600 !important;
}

[data-testid="stExpander"] > summary:hover p,
[data-testid="stExpander"] > summary:hover span,
[data-testid="stExpander"] > summary:focus p,
[data-testid="stExpander"] > summary:focus span {
    color: var(--wc-turquoise) !important;
}

/* --- EXPLICITLY RESET MOBILE NAV --- */
/* The above global overrides will hit mobile_nav since CSS structurally applies them globally. 
   We must rewrite them here with higher specificity, otherwise the mobile bar turns white! */
.st-key-mobile_nav [data-testid="stExpander"] {
    background: linear-gradient(135deg, var(--wc-dark) 0%, #162236 100%) !important;
    border: none !important;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.22) !important;
}

.st-key-mobile_nav [data-testid="stExpander"] > summary {
    background: transparent !important;
    padding: 0.65rem 1.25rem !important;
}

.st-key-mobile_nav [data-testid="stExpander"] > summary:hover {
    background: transparent !important;
}

.st-key-mobile_nav [data-testid="stExpanderDetails"] {
    background: transparent !important;
    padding: 0.25rem 0.75rem 0.75rem !important;
}

.st-key-mobile_nav [data-testid="stExpander"] > summary p,
.st-key-mobile_nav [data-testid="stExpander"] > summary span,
.st-key-mobile_nav [data-testid="stExpander"] > summary:hover p,
.st-key-mobile_nav [data-testid="stExpander"] > summary:hover span,
.st-key-mobile_nav [data-testid="stExpander"] > summary:focus p,
.st-key-mobile_nav [data-testid="stExpander"] > summary:focus span {
    color: var(--wc-gold) !important;
}

/* ===== Sliders ========================================= */
/* Apply explicitly styling to slider components so Brave matches the theme */
.stSlider div[data-baseweb="slider"] {
    padding-top: 0.5rem;
}

/* Thumb/handle */
.stSlider div[role="slider"] {
    background-color: var(--wc-turquoise) !important;
    border: 2px solid white !important;
    box-shadow: 0 0 0 2px var(--wc-turquoise) !important;
    width: 20px !important;
    height: 20px !important;
    border-radius: 50% !important;
}

/* Tooltips generated from slider */
.stSlider [role="tooltip"] {
    background-color: var(--wc-dark) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    padding: 0.2rem 0.5rem !important;
}
</style>
"""
