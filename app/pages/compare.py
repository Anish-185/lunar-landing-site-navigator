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
first = sc["site_id"] if sc["site_id"] in options else ui.DEFAULT_SITE
defaults = [first] + [s for s in ("change_7_target", "artemis_nobile_rim_2", "artemis_haworth",
                                  "artemis_mons_mouton_plateau") if s != first][:3]
cols = st.columns(4)
picks = []
for i, c in enumerate(cols):
    with c:
        on = st.checkbox(f"Scenario {i + 1}", value=True, key=f"cmp_on_{i}")
        sid = st.selectbox("Site", options, index=options.index(defaults[i]), format_func=ui._site_label,
                           key=f"cmp_site_{i}", label_visibility="collapsed", disabled=not on)
        d = st.date_input("Landing date (UTC)", value=sc["start"].date(), key=f"cmp_date_{i}", disabled=not on,
                          min_value=dt.date(2023, 1, 1), max_value=dt.date(2035, 12, 31))
        if on:
            picks.append((i + 1, sid, pd.Timestamp(d, tz="UTC") + (sc["start"] - sc["start"].normalize())))

rows = []
for n, sid, start in picks:
    s = engine.load_site(sid)
    _, summ, _ = ui.run(sid, s.lat, s.lon, start, sc["days"], sc["mast"], sc["lander_key"])
    rows.append({"label": f"{n}. {s.name}, {start:%-d %b %Y}", **summ})  # numbered: the same site may repeat
if not rows:
    st.info("Tick at least one scenario to compare.", icon=":material/info:")
    st.stop()
df = pd.DataFrame(rows)
table = pd.DataFrame({
    "Sunlit (%)": df["pct_sunlit"], "Link usable (%)": df["pct_link"], "Sun and link (%)": df["pct_both"],
    "Longest night (h)": df["longest_night_h"], "Longest blackout (h)": df["longest_blackout_h"],
    "Lowest battery (%)": 100 * df["min_soc"], "Eclipses": df["eclipses"],
}, index=df["label"]).T
higher_better = {"Sunlit (%)", "Link usable (%)", "Sun and link (%)", "Lowest battery (%)"}


def _best(row):
    target = row.max() if row.name in higher_better else row.min()
    return ["background-color: rgba(246,185,74,.22); font-weight: 600" if v == target and len(row) > 1 else ""
            for v in row]


st.dataframe(table.style.apply(_best, axis=1).format("{:.0f}"), width="stretch")
surv = " ".join(f"{'✓' if s else '✗'} {lab}: battery {'survives' if s else 'fails'}."
                for lab, s in zip(df["label"], df["survives"]))
st.caption(f"Lower is better for nights, blackouts and eclipses. {surv}")
st.plotly_chart(plots.compare_bars(df), config=plots.CONFIG, key="cmp_bars")
st.caption("Share of the mission with sunlight (gold), a usable link to Earth (blue) and both at once (white).")
with st.expander("Why each scenario scores the way it does"):
    for _, r in df.iterrows():
        st.markdown(f"**{r['label']}**")
        st.markdown("\n".join(f"- {x}" for x in r["reasons"]))
