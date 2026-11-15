"""Site: will this spot keep the lights on and the line to Earth open, and can you land there?"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui  # noqa: E402

from navigator import engine, landing, plots, scores  # noqa: E402

sc = ui.scenario()
site = sc["site"]
tl, summ, cd = ui.run_sc(sc)
verdict = scores.verdict(summ)
r0 = tl.iloc[0]
tile = None if site.custom else engine.load_tile(site.id)
light = landing.landing_light(tile, float(r0["sun_az"]), float(r0["sun_el"]), sc["heading"],
                              site_horizon=site.horizon(sc["mast"]), az_grid=site.az)

ui.site_header(sc)
if not site.has_terrain:
    st.info("No terrain model covers this site, so the horizon is a smooth sphere. Treat sunlight and Earth "
            "visibility as upper bounds.", icon=":material/info:")

# --- the three verdicts ---
power_reasons = [r for r in summ["reasons"] if r.startswith(("Sunlit", "Longest night", "Battery", "Earth eclipses"))]
comms_reasons = [r for r in summ["reasons"] if r.startswith(("Direct-to-Earth", "Longest comms", "Earth skims"))]
c1, c2, c3 = st.columns(3)
c1.markdown(ui.card("Power", "sun", plots.SUN, verdict["power"], f"{summ['pct_sunlit']:.0f}", "% of the mission sunlit",
                    power_reasons), unsafe_allow_html=True)
c2.markdown(ui.card("Comms", "satellite-dish", plots.EARTH, verdict["comms"], f"{summ['pct_link']:.0f}",
                    "% with a usable link to Earth", comms_reasons), unsafe_allow_html=True)
c3.markdown(ui.card("Landing light", "plane-landing", plots.TERRAIN, light["rating"], f"{light['sun_el']:.1f}°",
                    "Sun elevation at touchdown", light["reasons"]), unsafe_allow_html=True)

chips = [ui.countdown_chip(cd, "sunset", "sunset", plots.SUN, "Next sunset"),
         ui.countdown_chip(cd, "sunrise", "sunrise", plots.SUN, "Next sunrise"),
         ui.countdown_chip(cd, "earthset", "earth", plots.EARTH, "Next Earthset"),
         ui.countdown_chip(cd, "earthrise", "earth", plots.EARTH, "Next Earthrise")]
st.markdown(f"<div class='g-chips'>{''.join(chips)}</div>", unsafe_allow_html=True)
st.caption(f"Countdowns from touchdown. The ± window comes from LOLA's height error ({cd['sigma_z_m']:.1f} m) "
           "at the terrain that sets the horizon.")

if not sc["expert"]:
    both = summ["pct_both"]
    st.markdown(
        f"<p class='g-say'>Over {sc['days']} days the <span class='sun'>Sun</span> lights this spot "
        f"{summ['pct_sunlit']:.0f}% of the time and <span class='earth'>Earth</span> is reachable "
        f"{summ['pct_link']:.0f}% of the time; you get both at once {both:.0f}% of the time. "
        f"The longest night lasts {summ['longest_night_h']:.0f} hours and the longest silence from Earth "
        f"{summ['longest_blackout_h']:.0f} hours. "
        + ("The battery makes it through." if summ["survives"] else "The battery does not make it through.")
        + "</p>", unsafe_allow_html=True)
else:
    m = st.columns(6)
    m[0].metric("Sunlit", f"{summ['pct_sunlit']:.1f} %")
    m[1].metric("Link usable", f"{summ['pct_link']:.1f} %")
    m[2].metric("Both", f"{summ['pct_both']:.1f} %")
    m[3].metric("Longest night", f"{summ['longest_night_h']:.0f} h")
    m[4].metric("Longest blackout", f"{summ['longest_blackout_h']:.0f} h")
    m[5].metric("Lowest battery", f"{100 * summ['min_soc']:.0f} %")

# --- sky panorama ---
st.markdown("### The sky from the site")
st.plotly_chart(plots.sky_panorama(site, tl, sc["mast"]), config=plots.CONFIG, key="sky")
st.caption("Panorama of the whole horizon: compass direction across, elevation up. Grey is the terrain skyline "
           "(hover for the ridge that sets it). Dotted lines trace the Sun (gold) and Earth (blue) over the "
           "mission; press Play to move their discs, drawn to scale in elevation.")

# --- timeline ---
st.markdown("### Hour by hour")
ev = st.plotly_chart(plots.timeline(tl), config=plots.CONFIG, key="timeline", on_select="rerun",
                     selection_mode="points")
st.caption("Top: how far the Sun (gold) and Earth (blue) clear the terrain; gold shading marks sunlight, red "
           "crosses mark eclipses. Middle: link quality (blue good, pale blue marginal, orange poor, red none). "
           "Bottom: battery charge with the 20 % floor. Click a dark stretch to see which ridge is to blame.")

# --- blame the ridge ---
dark = ui.dark_periods(tl)
if len(dark):
    st.markdown("### Who turned out the lights?")
    pts = ev.selection.points if ev and ev.selection else []
    if pts:
        clicked = pd.Timestamp(pts[0]["x"]).tz_localize("UTC") if pd.Timestamp(pts[0]["x"]).tzinfo is None else pd.Timestamp(pts[0]["x"])
        hit = dark[(dark["start"] <= clicked) & (dark["end"] >= clicked)]
        if len(hit):
            st.session_state["dark_pick"] = int(hit.index[0])
    if st.session_state.get("dark_pick", 0) >= len(dark):
        st.session_state["dark_pick"] = 0
    label = lambda i: (f"{dark.loc[i, 'what']}: {dark.loc[i, 'hours']:.0f} h from "
                       f"{dark.loc[i, 'start']:%-d %b %H:%M} UTC")
    pick = st.selectbox("Dark period", dark.index, format_func=label, key="dark_pick")
    d = dark.loc[pick]
    i = min(int(pd.DatetimeIndex(tl["utc"]).searchsorted(d["start"])), len(tl) - 1)
    r = tl.iloc[i]
    body = d["body"]
    j, k = site.mast_row(sc["mast"]), int(r[f"{body}_occ"])
    hidden = r[f"{body}_clear"] + r[f"{body}_r"] <= 0
    if hidden:
        line = scores.blame_at(site, sc["mast"], body, float(r[f"{body}_az"]), float(r[f"{body}_el"]), r["utc"])
    elif body == "earth" and r["dsn"]:
        line = f"Earth only {r['earth_clear']:.1f}° above the terrain: too low for a clean link (multipath)."
    elif body == "earth":
        line = "No Deep Space Network dish can see the Moon then."
    else:
        line = "The Sun is partly hidden or eclipsed."
    st.markdown(f"<p class='g-say'>{line}</p>", unsafe_allow_html=True)
    ox, oy = site.occ_x[j, k], site.occ_y[j, k]
    if hidden and site.has_terrain and np.isfinite(ox) and site.dist[j, k] >= 500 and site.lat <= -80:
        name = str(site.occ_name[j, k]) or "ridge"
        if st.button(f"Show the {name} ridge on the map", icon=":material/location_on:"):
            st.session_state["occluder_marker"] = (float(ox), float(oy), name)
            st.switch_page(Path(__file__).with_name("map.py"))

# --- landing zone ---
o = None if site.custom else ui.odds(site.id, sc["start"], sc["days"], sc["lander_key"])
rel = None if site.custom else ui.relief(site.id)
if o is not None and rel is not None:
    st.markdown("### Landing-zone odds")
    a, b = st.columns([1, 2])
    a.markdown(ui.card("Odds of a good landing", "locate-fixed", plots.SUN,
                       "good" if o["p_success"] >= 0.8 else "caution" if o["p_success"] >= 0.4 else "bad",
                       f"{100 * o['p_success']:.0f}", f"% of {o['n']} landing points pass all four",
                       [f"Landing ellipse: σ = {sc['lander']['ellipse_sigma_m']} m on each axis.",
                        "Each point has its own horizon, slope and distance to permanent shadow.",
                        "Slope limit 10°: NASA's Artemis III requirement (over 100 m)."]), unsafe_allow_html=True)
    a.plotly_chart(plots.criteria_bars(o["rates"]), config=plots.CONFIG, key="crit")
    b.plotly_chart(plots.odds_scatter(rel, o), config=plots.CONFIG, key="odds")
    st.caption("Right: the 200 precomputed landing points over 20 m LOLA relief; gold circles pass slope, battery, "
               "link and touchdown light, red crosses fail at least one (hover for which). Left: share of points "
               "passing each test. Craters smaller than ~40 m are not in the 20 m terrain.")
elif site.custom:
    st.info("Landing-zone odds need precomputed ellipse points, which exist for catalog polar sites only.",
            icon=":material/info:")

with st.expander("Would a taller mast help?"):
    mt = ui.mast_table(site.id, site.lat, site.lon, sc["start"], sc["days"], sc["lander_key"])
    st.plotly_chart(plots.mast_curve(mt, sc["mast"]), config=plots.CONFIG, key="mast_curve")
    st.caption("Sunlight (gold) and usable link (blue) for the same mission with the solar array or antenna raised "
               "from 1 to 20 m. The dashed line marks 10 m, the class of NASA's Vertical Solar Array Technology masts.")

if not site.custom and site.lat <= -80:
    with st.expander("Science vs engineering: ice is in the dark, power is in the light"):
        pt = ui.pareto_table(site.id, sc["start"], sc["days"], sc["lander_key"])
        st.plotly_chart(plots.pareto_figure(pt), config=plots.CONFIG, key="pareto")
        st.caption("Each point is a landing point in this ellipse (grey) or a catalog site (white diamond), same dates. "
                   "Across: distance to the nearest permanently shadowed region (where water ice can survive). Up: "
                   "share of the mission with both Sun and a link. Gold joins the best trade-offs: nothing is both "
                   "closer to the shadow and better lit.")


# --- decision brief ---
st.markdown("### Take it to the review")
b1, b2 = st.columns([1, 2])
if b1.button("Prepare the decision brief", icon=":material/description:"):
    from navigator import brief, replan

    with st.spinner("Writing the brief..."):
        pb_rows = []
        if site.id in replan.candidate_sites():
            grid = replan.grid(replan.candidate_sites(), sc["start"], sc["lander"], sc["days"], span_days=30)
            pb = replan.plan_b(grid, site.id, sc["start"])
            for key, title in (("other_site", "Another site, same day"), ("same_site", "Same site, later day"),
                               ("best", "Best within 30 days")):
                r = pb[key]
                alt = replan.explain(r["site_id"], r["date"], sc["lander"], sc["days"])
                pb_rows.append({"title": title, "site": r["name"], "date": f"{r['date']:%-d %b %Y %H:%M}",
                                "pct_both": alt["pct_both"], "changed": ", ".join(replan.what_changed(summ, alt))})
        html_doc = brief.render(
            {"name": site.name, "lat": site.lat, "lon": site.lon, "start": sc["start"], "days": sc["days"],
             "mast": sc["mast"], "lander": sc["lander"]["name"], "horizon_source": site.horizon_source},
            summ, verdict, light, o, pb_rows,
            [plots.timeline(tl).to_html(full_html=False, include_plotlyjs="cdn")],
            ["Sunlit = any part of the Sun's disc above the terrain (NASA AVGVISIB definition).",
             "Link usable = Earth ≥ 2° above the terrain and a DSN complex sees the Moon ≥ 10° (thresholds are ours).",
             "Battery: single bucket, starts full, must stay above 20%. Lander numbers are illustrative unless cited.",
             "Slope limit 10° (NASA Artemis III landing requirement, 100 m baseline); our slope is 20 m LOLA.",
             "Terrain: LOLA 20 m near field + 80 m far field; craters smaller than ~40 m are not resolved."],
            ["LOLA DEMs, PGDA product 90 (Barker et al. 2023)", "LOLA illumination maps, PGDA product 69 "
             "(Mazarico et al. 2011)", "NAIF SPICE DE440 and lunar PCK", "NASA-AMMOS MMGIS Sightline (Apache-2.0)",
             "USGS Gazetteer of Planetary Nomenclature", "NASA Artemis III landing requirements (NTRS 20250009323)"])
        st.session_state["brief_html"] = html_doc
if "brief_html" in st.session_state:
    b1.download_button("Download the brief (HTML)", st.session_state["brief_html"].encode(),
                       file_name=f"gnomon_brief_{site.id}_{sc['start']:%Y%m%d}.html", mime="text/html",
                       icon=":material/download:")
b1.download_button("Download the hourly series (CSV)", tl.drop(columns=["sun_occ", "earth_occ"]).to_csv(index=False).encode(),
                   file_name=f"gnomon_{site.id}_{sc['start']:%Y%m%dT%H%M}Z.csv", mime="text/csv",
                   icon=":material/table:", key="csv_all")
b2.caption("The brief is one HTML page: verdicts with reasons, landing-zone odds, Plan B, assumptions and sources. "
           "Open it and print to PDF. The CSV has every hourly number behind this page.")
