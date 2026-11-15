"""Compare: up to four site + date scenarios side by side, best value per row highlighted."""

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui  # noqa: E402

from navigator import engine, plots  # noqa: E402

sc = ui.scenario()
st.markdown("# Compare")
st.markdown("<p class='g-lede'>Four candidates, same lander, same mission length. The best value in each row is "
            "highlighted in gold.</p>", unsafe_allow_html=True)

options = [s for s in ui._site_options() if s != ui.CUSTOM]
if st.button("Equator vs pole", icon=":material/school:", help="Apollo 11 against the Shackleton rim, same dates."):
    st.session_state.update({"cmp_site_0": "apollo_11", "cmp_site_1": "change_7_target", "cmp_on_0": True,
                             "cmp_on_1": True, "cmp_on_2": False, "cmp_on_3": False})
    st.rerun()
first = sc["site_id"] if sc["site_id"] in options else ui.DEFAULT_SITE
defaults = [first] + [s for s in ("change_7_target", "artemis_nobile_rim_2", "artemis_haworth",
                                  "artemis_mons_mouton_plateau") if s != first][:3]
for i in range(4):
    st.session_state.setdefault(f"cmp_on_{i}", True)
    st.session_state.setdefault(f"cmp_site_{i}", defaults[i])
cols = st.columns(4)
picks = []
for i, c in enumerate(cols):
    with c:
        on = st.checkbox(f"Scenario {i + 1}", key=f"cmp_on_{i}")
        sid = st.selectbox("Site", options, format_func=ui._site_label,
                           key=f"cmp_site_{i}", label_visibility="collapsed", disabled=not on)
        d = st.date_input("Landing date (UTC)", value=sc["start"].date(), key=f"cmp_date_{i}", disabled=not on,
                          min_value=dt.date(2023, 1, 1), max_value=dt.date(2035, 12, 31))
        if on:
            picks.append((i + 1, sid, pd.Timestamp(d, tz="UTC") + (sc["start"] - sc["start"].normalize())))

rows = []
for n, sid, start in picks:
    s = engine.load_site(sid)
    _, summ, _ = ui.run(sid, s.lat, s.lon, start, sc["days"], sc["mast"], sc["lander_key"], sc["relay"])
    rows.append({"label": f"{n}. {s.name}, {start:%-d %b %Y}",  # numbered: the same site may repeat
                 "col": f"{n}. {s.name.split(' (')[0]}, {start:%-d %b}", **summ})  # short, so four columns fit
if not rows:
    st.info("Tick at least one scenario to compare.", icon=":material/info:")
    st.stop()
df = pd.DataFrame(rows)
# Build from the label-indexed frame: passing Series with a 0..n index plus index=labels would realign every value
# to NaN (the v1 table showed "None" in every cell).
by = df.set_index("col")
table = pd.DataFrame({
    "Sunlit (%)": by["pct_sunlit"], "Link usable (%)": by["pct_link"], "Sun and link (%)": by["pct_both"],
    "Longest night (h)": by["longest_night_h"], "Longest blackout (h)": by["longest_blackout_h"],
    "Lowest battery (%)": 100 * by["min_soc"], "Eclipses": by["eclipses"],
}).astype(float).T
higher_better = {"Sunlit (%)", "Link usable (%)", "Sun and link (%)", "Lowest battery (%)"}


def _best(row):
    target = row.max() if row.name in higher_better else row.min()
    return ["background-color: rgba(244,184,96,.22); font-weight: 600" if v == target and len(row) > 1 else ""
            for v in row]


st.dataframe(table.style.apply(_best, axis=1).format("{:.0f}"), width="stretch")
surv = " ".join(f"{'✓' if s else '✗'} {lab}: battery {'survives' if s else 'fails'}."
                for lab, s in zip(df["label"], df["survives"]))
st.caption(f"Lower is better for nights, blackouts and eclipses. {surv}")
st.plotly_chart(plots.compare_bars(df), config=plots.CONFIG, key="cmp_bars")
st.caption("Share of the mission with sunlight (gold), a usable link to Earth (blue) and both at once (white).")
with st.expander("Why is the pole so strange?"):
    st.markdown("""
At Apollo 11, near the equator, the Sun climbs high, crosses the sky and sets: about two weeks of day, two weeks of
night, like clockwork. Earth hangs almost still, high in the west, because the Moon keeps one face to us.

At the south pole the Sun never climbs. The Moon's axis is tilted only 1.5° to the Sun, so the Sun **circles the
horizon** once a month, never more than a degree or two up. A ridge 30 km away can hide it for days; a peak a few
hundred metres higher can keep it in view for weeks. That is why sites only a few hundred metres apart can differ
by tens of percent in sunlight, and why Gnomon names the ridge to blame.

Earth does something stranger: it **bobs up and down** by several degrees over a month as the Moon wobbles
(libration). Near the pole that is enough to drop Earth behind the terrain for days, cutting the radio link,
and when it is just above the horizon the signal bounces off the ground (multipath).

Press **Equator vs pole** above to see both at once.
""")

with st.expander("Why each scenario scores the way it does"):
    for _, r in df.iterrows():
        st.markdown(f"**{r['label']}**")
        st.markdown("\n".join(f"- {x}" for x in r["reasons"]))
