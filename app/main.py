import streamlit as st
import sys
import os

# Add app directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="FIFA World Cup 2026 Simulation Explorer",
    page_icon="\U0001f3c6",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from ui.theme import inject_css

inject_css()

# Define pages
pages = [
    st.Page("pages/landing.py", title="Home", icon="\U0001f3c6", default=True),
    st.Page("pages/competition.py", title="Competition Explorer", icon="\U0001f4ca"),
    st.Page("pages/team.py", title="Team Explorer", icon="\u26bd"),
    st.Page("pages/city.py", title="City Explorer", icon="\U0001f3d9\ufe0f"),
]

pg = st.navigation(pages, position="hidden")

# ── Navigation ───────────────────────────────────────────────────────────────

# Desktop Navigation — pure HTML nav so we own the layout entirely.
# Hidden on mobile via CSS (.st-key-desktop_nav).
with st.container(key="desktop_nav"):
    st.markdown(
        """
    <nav class="wc-navbar">
        <div class="wc-nav-brand">🏆 FIFA WC 2026</div>
        <div class="wc-nav-links">
            <a href="" class="wc-nav-link">🏆 Home</a>
            <a href="competition" class="wc-nav-link">📊 Competition</a>
            <a href="team" class="wc-nav-link">⚽ Teams</a>
            <a href="city" class="wc-nav-link">🏙️ City</a>
        </div>
    </nav>
    """,
        unsafe_allow_html=True,
    )

# Mobile Navigation (Hamburger / Expander) — hidden on desktop via CSS (.st-key-mobile_nav)
with st.container(key="mobile_nav"):
    with st.expander("🏆 FIFA WC 2026  ·  Menu", expanded=False):
        st.page_link(
            "pages/landing.py", label="\U0001f3c6 Home", use_container_width=True
        )
        st.page_link(
            "pages/competition.py",
            label="\U0001f4ca Competition",
            use_container_width=True,
        )
        st.page_link("pages/team.py", label="\u26bd Teams", use_container_width=True)
        st.page_link(
            "pages/city.py", label="\U0001f3d9\ufe0f City", use_container_width=True
        )

st.divider()

pg.run()
