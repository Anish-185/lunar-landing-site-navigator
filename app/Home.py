"""Gnomon (Lunar Landing Site Navigator): Streamlit entry point. Draws the shared sidebar once, then runs the page.

Run: streamlit run app/Home.py. The app makes no network calls: everything comes from data/derived/.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui  # noqa: E402

PAGES = Path(__file__).resolve().parent / "views"  # not "pages": Streamlit would auto-register those and bypass this router on deep links

ui.setup()
nav = st.navigation([
    st.Page(PAGES / "site.py", title="Site", icon=":material/wb_twilight:", default=True),
    st.Page(PAGES / "compare.py", title="Compare", icon=":material/compare_arrows:"),
    st.Page(PAGES / "replan.py", title="Slip Replanner", icon=":material/event_repeat:"),
    st.Page(PAGES / "map.py", title="Map", icon=":material/map:"),
    st.Page(PAGES / "athena.py", title="Athena replay", icon=":material/history:"),
    st.Page(PAGES / "evidence.py", title="Evidence", icon=":material/verified:"),
], position="top")
st.session_state["_scenario"] = ui.sidebar()
st.session_state["_routed"] = True
try:
    nav.run()
finally:
    st.session_state["_routed"] = False
