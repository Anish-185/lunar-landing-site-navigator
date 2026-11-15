"""Athena replay: IM-2, 6 March 2025. What our planner sees, and what orbital maps cannot."""

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui  # noqa: E402

from navigator import engine, geo, landing, plots  # noqa: E402

ui.scenario()
TOUCHDOWN = pd.Timestamp("2025-03-06T17:28:50Z")
AP = "https://www.expressandstar.com/world-news/private-lunar-lander-dead-after-landing-in-crater-near-moons-south-pole-5717533"
CAUSE = "https://gizmodo.com/intuitive-machines-reveals-why-its-moon-lander-faceplanted-into-a-crater-2000602752"
LROC = "https://lroc.im-ldi.com/images/1408"

actual, target = engine.load_site("im2_actual"), engine.load_site("im2_target")
nova = engine.landers()["nova_c"]
dist_m = float(geo.great_circle_m(actual.lat, actual.lon, target.lat, target.lon))


@st.cache_data(show_spinner="Replaying 6 March 2025...")
def _replay():
    tl = engine.timeline(actual, TOUCHDOWN.floor("1h"), 10, 2.0, nova)
    eph = engine.sun_earth_azel(actual.lat, actual.lon, [TOUCHDOWN]).iloc[0]
    tile = engine.load_tile("im2_actual")
    light = landing.landing_light(tile, float(eph["sun_az"]), float(eph["sun_el"]))
    odds_t = landing.ellipse_odds(engine.load_tile("im2_target"), engine.timeline(target, TOUCHDOWN.floor("1h"), 10,
                                                                                  2.0, nova), nova)
    return tl, eph, light, odds_t


tl, eph, light, odds_t = _replay()
snap = np.load(engine.DERIVED / "shadow" / "im2_actual_sun_20250306T172850Z.npz")
st.markdown("# Athena replay")
st.markdown("<p class='g-lede'>On 6 March 2025 Intuitive Machines' Athena touched down on Mons Mouton, 160 km from "
            "the south pole, tipped onto its side in a small crater and went quiet 13 hours later. Here is the "
            "landing through Gnomon, step by step, including the part no orbital map could show.</p>",
            unsafe_allow_html=True)

st.markdown("## 1. A few hundred metres off target")
a, b = st.columns([1, 1.4])
a.markdown(f"<p class='g-say'>Athena came down about 250 m from its target, as reported by "
           f"<a href='{AP}'>AP</a>. LROC's published positions (target to two decimals) put the resting spot "
           f"{dist_m:.0f} m away. Either way it is several times the {nova['ellipse_sigma_m']} m sigma we assume "
           f"for Nova-C (an illustrative number): far outside the ellipse a plan would be built around.</p>",
           unsafe_allow_html=True)
rel = ui.relief("im2_actual")
odds_a = ui.odds("im2_actual", TOUCHDOWN.floor("1h"), 10, "nova_c")
tx, ty = geo.latlon_to_xy(target.lat, target.lon, engine.COARSE_DEM)
ax, ay = geo.latlon_to_xy(actual.lat, actual.lon, engine.COARSE_DEM)
b.plotly_chart(plots.odds_scatter(rel, odds_a, [(tx, ty, "Target", plots.EARTH), (ax, ay, "Athena", plots.ALARM)],
                                  height=460), config=plots.CONFIG, key="ath_map")
b.caption("20 m LOLA relief around the resting spot, with 200 simulated landings (σ = 50 m, illustrative), the "
          "published target (blue diamond) and the resting spot (red diamond).")

st.markdown("## 2. The light at touchdown")
c = st.columns(4)
c[0].metric("Sun elevation", f"{light['sun_el']:.1f}°")
c[1].metric("Sun azimuth", f"{light['sun_az']:.0f}°")
c[2].metric("1 m boulder's shadow", f"{light['boulder_shadow_m']:.0f} m")
c[3].metric("Landing zone in terrain shadow", f"{light['shadow_pct']:.0f} %", help="At 20 m resolution.")
st.markdown(f"<p class='g-say'>The Sun stood {light['sun_el']:.1f}° above the horizon. At that angle every metre of "
            f"relief throws a {light['boulder_shadow_m']:.0f} m shadow. Intuitive Machines later blamed long shadows "
            f"and dim polar light for confusing the lander's navigation (<a href='{CAUSE}'>report</a>). Our "
            "landing-light card, working from 20 m orbital terrain, rates this touchdown "
            f"<b>{ui.STATUS[light['rating']][0]}</b>: {' '.join(light['reasons'][:2])} Hold that thought.</p>",
            unsafe_allow_html=True)

st.markdown("## 3. The odds, had it landed upright")
st.markdown(f"<p class='g-say'>Running a 10-day mission at the 200 landing points around the target: "
            f"<b>{100 * odds_t['p_success']:.0f}%</b> pass slope, battery, link and touchdown light. "
            f"Sunlit {tl['sunlit'].mean():.0%} of those 10 days at the resting spot, link usable "
            f"{tl['link'].mean():.0%}. By orbital data, Mons Mouton was a good choice.</p>", unsafe_allow_html=True)
st.plotly_chart(plots.criteria_bars(odds_t["rates"]), config=plots.CONFIG, key="ath_rates")
st.caption("Share of simulated landing points around the target passing each test (Nova-C preset: illustrative "
           "power numbers; a tipped lander's panels are not modelled).")

st.markdown("## 4. What the map cannot see")
grid = snap["grid"]
fig = go.Figure(go.Heatmap(z=np.where(grid == 1, 1, 0)[::-1], colorscale=[[0, "#05071A"], [1, plots.SUN]],
                           zmin=0, zmax=1, showscale=False, hoverinfo="skip",
                           x=np.arange(grid.shape[1]) * 20 - 300, y=np.arange(grid.shape[0]) * 20 - 300))
fig.add_shape(type="circle", x0=-10, x1=10, y0=-10, y1=10, line=dict(color=plots.ALARM, width=2))
fig.update_layout(template="gnomon", height=380, xaxis=dict(title="m", scaleanchor="y"), yaxis=dict(title="m"),
                  margin=dict(l=50, r=10, t=20, b=40))
d1, d2 = st.columns([1, 1.2])
d1.plotly_chart(fig, config=plots.CONFIG, key="ath_shadow")
d1.caption(f"NASA MMGIS sightmap at touchdown on 20 m LOLA terrain, 600 m square: {100 * (grid == 1).mean():.1f}% lit "
           "(gold). The red circle is the size of Athena's 20 m crater: one pixel.")
depth = np.array([0.1, 0.2]) * 20
reach = depth / np.tan(np.radians(light["sun_el"]))
d2.markdown(f"<p class='g-say'>The 20 m terrain says the whole landing zone was in sunlight. LROC found Athena "
            f"<a href='{LROC}'>on its side in a 20-metre crater</a>, a single pixel in that map. A small lunar crater "
            f"is typically 0.1–0.2 of its width deep (illustrative), {depth[0]:.0f}–{depth[1]:.0f} m here; with the "
            f"Sun at {light['sun_el']:.1f}° its rim throws a {reach[0]:.0f}–{reach[1]:.0f} m shadow, so the floor of "
            "a 20 m crater is dark. We tried NASA's 5 m shape-from-shading terrain (PGDA product 104): its nearest "
            "region, Leibnitz Beta Plateau, starts 30 km south of Athena, so no public map resolves this crater.</p>"
            "<p class='g-say'>That is why landing ellipses carry margins, why landers carry hazard-avoidance "
            "cameras, and why Gnomon reports odds over the whole ellipse instead of one perfect point.</p>",
            unsafe_allow_html=True)

if st.button("Load Athena's landing in the planner", icon=":material/rocket_launch:", type="primary"):
    ui.preset(site="im2_actual", date=dt.date(2025, 3, 6), time=dt.time(17, 0), days=10, lander="nova_c", mast=2.0)
    st.switch_page(Path(__file__).with_name("site.py"))
