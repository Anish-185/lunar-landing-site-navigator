"""Slip Replanner: the launch moved. Which site and date still work, and what changes?"""

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui  # noqa: E402

from navigator import engine, plots, replan  # noqa: E402

sc = ui.scenario()
lander = sc["lander"]
st.markdown("# Slip Replanner")
st.markdown("<p class='g-lede'>Launches slip. At the pole that can turn two weeks of sunshine into two weeks of night. "
            "Move the slip and see every candidate site and landing date re-ranked, with Plan B ready.</p>",
            unsafe_allow_html=True)

default_launch = (sc["start"] - pd.Timedelta(days=lander["cruise_days"])).date()
c1, c2, c3 = st.columns([1, 2, 1])
launch = c1.date_input("Planned launch (UTC)", value=default_launch, min_value=dt.date(2026, 11, 1),
                       max_value=dt.date(2028, 9, 30), key="rp_launch")
slip = c2.slider("Launch slip (days)", 0, 90, 42, key="rp_slip")
c3.metric("Cruise", f"{lander['cruise_days']:g} days", help=f"{lander['name']}: launch to landing.")
launch_t = pd.Timestamp(launch, tz="UTC") + (sc["start"] - sc["start"].normalize())
planned = replan.landing_date(launch_t, lander["cruise_days"], 0)
slipped = replan.landing_date(launch_t, lander["cruise_days"], slip)
site_id = sc["site_id"] if sc["site_id"] in replan.candidate_sites() else ui.DEFAULT_SITE


@st.cache_data(show_spinner="Re-ranking every site and date...", max_entries=16)
def _grid(center: pd.Timestamp, lander_key: str, days: int):
    return replan.grid(replan.candidate_sites(), center, engine.landers()[lander_key], days)


@st.cache_data(show_spinner=False, max_entries=64)
def _explain(sid: str, date: pd.Timestamp, lander_key: str, days: int):
    return replan.explain(sid, date, engine.landers()[lander_key], days)


df = _grid(slipped, sc["lander_key"], sc["days"])
pb = replan.plan_b(df, site_id, slipped)
orig = pb["original"]
before = _explain(site_id, planned, sc["lander_key"], sc["days"])
now = _explain(site_id, orig["date"], sc["lander_key"], sc["days"])

name = engine.load_site(site_id).name
st.markdown(f"<p class='g-say'>Planned: {name}, landing {planned:%-d %b %Y}, Sun and link "
            f"{before['pct_both']:.0f}% of the time. After a {slip}-day slip you land {orig['date']:%-d %b %Y}: "
            f"{now['pct_both']:.0f}%, battery {'survives' if now['survives'] else 'fails'}"
            f"{'' if slip == 0 else ' (' + ', '.join(replan.what_changed(before, now)) + ')'}.</p>",
            unsafe_allow_html=True)

cards = [("After the slip", "rocket", plots.TERRAIN, orig, now, None),
         ("Plan B: another site, same day", "map", plots.EARTH, pb["other_site"], None, None),
         ("Plan B: same site, a later day", "timer", plots.SUN, pb["same_site"], None, None),
         ("Plan B: best on or after the slip", "telescope", plots.SUN, pb["best"], None, None)]
cols = st.columns(4)
for col, (title, ic, accent, row, summ, _) in zip(cols, cards):
    summ = summ or _explain(row["site_id"], row["date"], sc["lander_key"], sc["days"])
    rating = ("bad" if not summ["survives"] or summ["pct_both"] < 25 else "good" if summ["pct_both"] >= 60 else "caution")
    changed = [] if title == "After the slip" else ["What changed: " + ", ".join(replan.what_changed(now, summ)) + "."]
    col.markdown(ui.card(title, ic, accent, rating, f"{summ['pct_both']:.0f}", "% Sun and link",
                         [f"{row['name']}, land {row['date']:%-d %b %Y %H:%M} UTC.",
                          f"Battery {'survives' if summ['survives'] else 'fails'}; longest night "
                          f"{summ['longest_night_h']:.0f} h.", *changed]), unsafe_allow_html=True)
    if title != "After the slip" and col.button("Plan this", key=f"rp_go_{title}", icon=":material/arrow_outward:"):
        ui.preset(site=row["site_id"], date=row["date"].date(), time=row["date"].time(), lander=sc["lander_key"])
        st.switch_page(Path(__file__).with_name("site.py"))

st.markdown("### Every site, every landing day")
st.plotly_chart(plots.replan_heatmap(df, slipped, site_id), config=plots.CONFIG, key="rp_heat")
st.caption(f"Rows: candidate sites. Across: landing dates within 60 days of the slipped landing ({slipped:%-d %b %Y}, "
           f"dotted line). Colour: share of a {sc['days']}-day mission with both Sun and a usable link to Earth "
           "(brighter is better). Red crosses: the battery falls below 20 % on that plan.")
if sc["expert"]:
    st.download_button("Download the grid (CSV)", df.to_csv(index=False).encode(), "gnomon_replan.csv", "text/csv",
                       icon=":material/download:")
