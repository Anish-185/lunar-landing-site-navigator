"""Evidence: how far to trust the numbers. Ephemeris vs JPL Horizons, sunlight vs NASA's own maps, and a
hindcast of the landers that actually flew."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui  # noqa: E402

from navigator import engine, scores  # noqa: E402

sc = ui.scenario()
ROOT = engine.ROOT
st.markdown("# Evidence")
st.markdown("<p class='g-lede'>Every number on the other pages comes from the checks below. Where we disagree with "
            "NASA, we show by how much and why.</p>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _tables():
    hz = pd.read_csv(engine.DERIVED / "validation_horizons.csv")
    rng = pd.read_csv(engine.DERIVED / "validation_avgvisib_range.csv")
    return hz, rng


@st.cache_data(show_spinner="Re-flying the landers that went before...")
def _hindcast():
    rows = []
    for m in yaml.safe_load((ROOT / "pipeline" / "hindcast.yaml").read_text())["missions"]:
        site = engine.load_site(m["site_id"])
        sunset = scores.first_sunset(site, m["landing_utc"])
        rows.append({"Mission": m["name"], "Landed (UTC)": pd.Timestamp(m["landing_utc"]).strftime("%-d %b %Y %H:%M"),
                     "Our first sunset (UTC)": sunset.strftime("%-d %b %Y %H:%M") if pd.notna(sunset) else "none in 20 d",
                     "Reported end": m["reported_end"], "Ended by": m["ended_by"],
                     "Terrain": site.horizon_source, "Source": m["source_url"], "Quote": m["quote"]})
    return pd.DataFrame(rows)


hz, rng = _tables()
st.markdown("## 1. Where the Sun and Earth are")
c1, c2 = st.columns([1, 2])
c1.metric("Largest error vs JPL Horizons", f"{hz['sep'].max() * 3600:.3f} arcsec",
          help="Angular separation, Sun and Earth, 130 comparisons.")
c1.metric("Comparisons", f"{len(hz)}")
c2.markdown(f"<p class='g-say'>We compared our Sun and Earth positions with NASA JPL's Horizons system at "
            f"{len(hz)} moments: Apollo 11, the Shackleton rim and Malapert across 2027, and Athena's landing day. "
            f"The worst disagreement is {hz['sep'].max():.1e}°, which is the precision Horizons prints. Same "
            "ephemeris (DE440), same lunar frame, so it should agree, and it does.</p>", unsafe_allow_html=True)
if sc["expert"]:
    st.dataframe(hz.groupby(["site_id", "body"])["sep"].agg(["count", "max"]).rename(
        columns={"count": "epochs", "max": "max separation (deg)"}), width="stretch")

st.markdown("## 2. Long-run sunlight vs NASA's maps")
inside = int(rng["sun_in_range"].sum())
st.markdown(f"<p class='g-say'>NASA's LOLA team mapped how often each spot sees the Sun and Earth over 18.6 years "
            f"(PGDA product 69). On steep terrain those numbers change within a few hundred metres, so we compare "
            f"our value with NASA's own range within 420 m of each site. <b>Sun: inside NASA's range at {inside} of "
            f"{len(rng)} sites. Earth: inside at {int(rng['earth_in_range'].sum())}.</b></p>", unsafe_allow_html=True)
names = {s["id"]: s["name"] for s in engine.catalog()}
mark = lambda ok: "✓ inside" if ok else "✗ outside"
tab = pd.DataFrame({
    "Site": rng["site_id"].map(names),
    "NASA Sun (%)": 100 * rng["nasa_sun"], "Ours (%)": 100 * rng["our_sun"],
    "NASA range within 420 m (%)": [f"{100 * a:.0f}–{100 * b:.0f}" for a, b in zip(rng["nasa_sun_min"], rng["nasa_sun_max"])],
    "Sun": rng["sun_in_range"].map(mark),
    "NASA Earth (%)": 100 * rng["nasa_earth"], "Ours Earth (%)": 100 * rng["our_earth"],
    "Earth range (%)": [f"{100 * a:.0f}–{100 * b:.0f}" for a, b in zip(rng["nasa_earth_min"], rng["nasa_earth_max"])],
    "Earth": rng["earth_in_range"].map(mark),
})
st.dataframe(tab.style.format({c: "{:.1f}" for c in tab.columns if "(%)" in c and "range" not in c}),
             width="stretch", hide_index=True)
st.caption("✓ = our value lies within NASA's own minimum–maximum within 420 m of the site. Peak near Cabeus B is "
           "the one Sun miss: our 20 m near-field terrain sees ridges that NASA's 120 m map smooths away (with an "
           "80 m near field we get 16.8%, toward NASA's 19.7%). On the Blue Moon MK1 ridge NASA's own map runs from "
           "0% to 59.5% within 420 m: on a ridge, a few hundred metres is the difference between a peak of light "
           "and a pit of night.")

st.markdown("## 3. The landers that went before")
st.markdown("<p class='g-say'>Our first predicted sunset after each real landing, next to what the mission reported. "
            "Three of the four ended at nightfall; Athena did not get that far.</p>", unsafe_allow_html=True)
hc = _hindcast()
st.dataframe(hc.drop(columns=["Quote"]), width="stretch", hide_index=True,
             column_config={"Source": st.column_config.LinkColumn("Source", display_text="page")})
st.caption("Blue Ghost 1 and Apollo 11 lie outside our polar terrain, so their horizon is a smooth sphere; "
           "Chandrayaan-3 uses 240 m terrain. Reported ends are quoted from the linked pages: "
           + " ".join(f"{r['Mission']}: “{r['Quote']}”" for _, r in hc.iterrows()))

with st.expander("Method and known limits (docs/METHOD.md)"):
    st.markdown((ROOT / "docs" / "METHOD.md").read_text())
