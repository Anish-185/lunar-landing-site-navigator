"""Map: NASA's long-run sunlight and Earth visibility over the south pole, PSRs, and every catalog site."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui  # noqa: E402

from navigator import engine, geo, plots  # noqa: E402

sc = ui.scenario()


@st.cache_data(show_spinner=False)
def _layer():
    with np.load(engine.DERIVED / "map_avgvisib.npz") as z:
        return {k: z[k] for k in z.files}


@st.cache_resource(show_spinner=False)
def _psr():
    return plots.psr_traces(json.loads((engine.DERIVED / "psr_outlines.geojson").read_text()))


@st.cache_data(show_spinner=False)
def _sites(crs: str):
    rows = []
    for s in engine.catalog():
        if s["lat"] > -80:
            continue
        x, y = geo.latlon_to_xy(s["lat"], s["lon"], crs)
        rows.append({"id": s["id"], "name": s["name"], "short": s["name"].replace("Peak near ", ""),
                     "x_km": x / 1000, "y_km": y / 1000})
    return pd.DataFrame(rows)


layer = _layer()
sites = _sites(str(layer["crs"]))
st.markdown("# Map")
st.markdown("<p class='g-lede'>NASA's own long-run maps (LOLA, 18.6 years of sunlight and Earth visibility, PGDA "
            "product 69), averaged to 2.5 km. Click a site to plan it.</p>", unsafe_allow_html=True)
body = st.segmented_control("Layer", ["Sunlight", "Earth visibility"], default="Sunlight", key="map_layer")
marker = st.session_state.get("occluder_marker")
fig = plots.map_figure(layer, "earth" if body == "Earth visibility" else "sun", sites, _psr(), sc["site_id"],
                       marker)
event = st.plotly_chart(fig, config=plots.CONFIG, key="map", on_select="rerun", selection_mode="points")
st.caption("Polar stereographic view centred on the south pole (km). Brighter means more of the time with the Sun "
           "(gold) or Earth (blue) in view. Purple outlines are permanently shadowed regions larger than 3 km². "
           "Diamonds are catalog sites; a red cross marks a ridge picked on the Site page.")
pts = (event or {}).get("selection", {}).get("points", []) if isinstance(event, dict) or hasattr(event, "get") else []
picked = [p.get("customdata") for p in pts if p.get("customdata")]
if picked and picked[0] != sc["site_id"]:
    ui.preset(site=picked[0], lander="")
    st.switch_page(Path(__file__).with_name("site.py"))
if marker:
    if st.button("Clear the ridge marker", icon=":material/close:"):
        st.session_state.pop("occluder_marker", None)
        st.rerun()
