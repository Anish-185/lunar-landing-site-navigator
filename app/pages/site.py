"""Site: will this spot keep the lights on and the line to Earth open, and can you land there?"""

import sys
from pathlib import Path

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
st.plotly_chart(plots.timeline(tl), config=plots.CONFIG, key="timeline")
st.caption("Top: how far the Sun (gold) and Earth (blue) clear the terrain; gold shading marks sunlight, red "
           "crosses mark eclipses. Middle: link quality (blue good, pale blue marginal, orange poor, red none). "
           "Bottom: battery charge with the 20 % floor.")

if sc["expert"]:
    cols = ["utc", "sun_az", "sun_el", "sun_h", "sun_clear", "sun_frac", "eclipse", "eff_sun", "earth_az", "earth_el",
            "earth_h", "earth_clear", "band", "dsn", "link", "power_W", "soc"]
    st.download_button("Download the hourly series (CSV)", tl[cols].to_csv(index=False).encode(),
                       file_name=f"gnomon_{site.id}_{sc['start']:%Y%m%dT%H%M}Z.csv", mime="text/csv",
                       icon=":material/download:")
