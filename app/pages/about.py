import streamlit as st
import urllib.request
import re

st.set_page_config(
    page_title="About",
    page_icon="ℹ️",
)

@st.cache_data(ttl=3600)
def get_methodology_markdown():
    # Use the raw URL to reliably fetch the markdown text content
    url = "https://raw.githubusercontent.com/zvizdo/fifa-wc-2026-simulation/main/README.md"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
        
        # Extract everything from "## Match Prediction Model" to the next "## "
        match = re.search(r'(## Match Prediction Model.*?)(?=\n## |\Z)', content, re.DOTALL)
        if match:
            return match.group(1)
        return "Methodology content not found."
    except Exception as e:
        return f"Could not load methodology: {e}"

st.markdown(
    """
<div class="wc-hero">
    <h1>About the Project</h1>
    <p class="subtitle">
        Explore the codebase, read the underlying methodology, or support the project.
    </p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

tab_info, tab_methodology = st.tabs(["Project Info", "Methodology"])

with tab_info:
    # 1. Source code section
    st.markdown("#### <img src='https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png' width='25' style='vertical-align: middle; margin-bottom: 3px;'/> Source Code", unsafe_allow_html=True)
    st.caption("The complete codebase for the simulation engine and this web application is open source and available on GitHub.")
    st.link_button("View on GitHub", url="https://github.com/zvizdo/fifa-wc-2026-simulation", width="content")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Articles section
    st.markdown('<div class="wc-section-header">📚 Articles</div>', unsafe_allow_html=True)
    st.markdown(
        """
        Read detailed walkthroughs and insights about how the simulation was built:
        * [**Simulating the 2026 FIFA World Cup**](https://medium.com/@anzekravanja/4be4693d66b3) - *Medium*
        * *More articles coming soon...*
        """
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Support section
    st.markdown('<div class="wc-section-header">💖 Support the Project</div>', unsafe_allow_html=True)
    st.success(
        "**Enjoying the simulation?**\n\n"
        "This project is a labor of love and completely open source. If you found it interesting or useful, "
        "consider supporting! Your donation would help cover server costs.",
        icon="✨"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button("Stripe 💳", url="https://donate.stripe.com/14A7sN9mJ9sTdVQ8aP3cc00", width="stretch")
    with c2:
        st.link_button("Venmo 📱", url="https://venmo.com/code?user_id=3846411489641618812&created=1773026723", width="stretch")
    with c3:
        st.link_button("Strike ⚡", url="https://strike.me/anzekravanja", width="stretch")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("Developed by Anže Kravanja")

with tab_methodology:
    st.markdown('<div class="wc-section-header">🔬 Methodology</div>', unsafe_allow_html=True)
    with st.spinner("Loading methodology from GitHub..."):
        methodology_md = get_methodology_markdown()
        st.markdown(methodology_md)