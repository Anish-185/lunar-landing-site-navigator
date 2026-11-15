"""Shared UI for every page: page setup, the sidebar (mirrored in the URL), cached scenario runs, and the small
HTML pieces (cards, chips, icons). Logic lives in navigator/; this file only wires it to Streamlit."""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from navigator import engine, events, landing, scores

APP = Path(__file__).resolve().parent
NAME, SUBTITLE = "Gnomon", "Lunar Landing Site Navigator"
GROUPS = {"artemis_region": "Artemis III region", "clps": "CLPS lander", "international": "International",
          "apollo": "Apollo"}
CUSTOM = "custom"
DEFAULT_START = "2027-01-18T12:00:00Z"
DEFAULT_SITE = "artemis_nobile_rim_2"
STATUS = {"good": ("Go", "circle-check"), "caution": ("Caution", "triangle-alert"), "bad": ("No-go", "octagon-x")}


# --- page setup ---

def icon(name: str) -> str:
    svg = (APP / "static" / "icons" / f"{name}.svg").read_text()
    return svg.split("-->", 1)[-1].strip().replace("\n", "")


def css() -> None:
    st.html(f"<style>{(APP / 'style.css').read_text()}</style>")


def setup(title: str = "Site") -> None:
    st.set_page_config(page_title=f"{title} | {NAME}", page_icon=":material/wb_twilight:",
                       layout="wide", initial_sidebar_state="auto")  # collapsed on phones
    css()


# --- sidebar state <-> URL ---

def _site_options() -> list[str]:
    order = list(GROUPS)
    sites = sorted(engine.catalog(), key=lambda s: (order.index(s["group"]), s["name"]))
    return [s["id"] for s in sites] + [CUSTOM]


def _site_label(sid: str) -> str:
    if sid == CUSTOM:
        return "Custom latitude / longitude"
    s = next(s for s in engine.catalog() if s["id"] == sid)
    return f"{s['name']} ({GROUPS[s['group']]})"


def _load_query_params() -> None:
    """First run of a session: take the scenario from the URL, so a shared link reproduces the view."""
    if st.session_state.get("_qp_loaded"):
        return
    qp = st.query_params
    opts = _site_options()
    ss = st.session_state
    ss.setdefault("site", qp.get("site") if qp.get("site") in opts else DEFAULT_SITE)
    try:
        t = pd.Timestamp(qp.get("t", DEFAULT_START))
        t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    except ValueError:
        t = pd.Timestamp(DEFAULT_START)
    ss.setdefault("date", t.date())
    ss.setdefault("time", t.time().replace(second=0, microsecond=0))
    num = lambda k, d, lo, hi: float(np.clip(float(qp.get(k, d)), lo, hi)) if _is_num(qp.get(k, d)) else d
    ss.setdefault("days", int(num("days", 7, 1, 60)))  # about a crewed surface stay
    ss.setdefault("mast", num("mast", 2.0, 1.0, 20.0))
    ss.setdefault("lat", num("lat", -89.45, -90.0, -80.0))
    ss.setdefault("lon", num("lon", -137.3, -180.0, 180.0))
    ss.setdefault("heading", num("heading", landing.DEFAULT_HEADING, 0.0, 359.0))
    ss.setdefault("lander", qp.get("lander") if qp.get("lander") in engine.landers() else "")
    ss.setdefault("mode", "Expert" if qp.get("mode") == "expert" else "Simple")
    ss.setdefault("relay", qp.get("relay") == "1")
    ss["_qp_loaded"] = True


def _is_num(v) -> bool:
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def preset(**kw) -> None:
    """Queue scenario fields (e.g. the Athena replay); applied before the sidebar widgets are drawn on the next
    run (a widget's value cannot change after it is drawn in the current run). Call st.rerun() or switch_page."""
    st.session_state["_pending"] = {**st.session_state.get("_pending", {}), **kw}


def sidebar() -> dict:
    _load_query_params()
    ss = st.session_state
    for k, v in ss.pop("_pending", {}).items():
        ss[k] = v
    with st.sidebar:
        st.markdown(f"<div style='font-family:Fraunces,serif;font-size:1.7rem;font-weight:300;line-height:1'>{NAME}</div>"
                    f"<div style='color:#A9A6C2;font-size:.85rem;margin:.2rem 0 1rem'>{SUBTITLE}</div>",
                    unsafe_allow_html=True)
        sid = st.selectbox("Landing site", _site_options(), format_func=_site_label, key="site")
        if sid == CUSTOM:
            c1, c2 = st.columns(2)
            c1.number_input("Latitude (°)", -90.0, -80.0, step=0.01, format="%.4f", key="lat")
            c2.number_input("Longitude (°E)", -180.0, 180.0, step=0.01, format="%.4f", key="lon")
            st.caption("Coarser terrain (160 m) than catalog sites.")
        c1, c2 = st.columns(2)
        c1.date_input("Landing date (UTC)", key="date", min_value=dt.date(2023, 1, 1), max_value=dt.date(2035, 12, 31))
        c2.time_input("Time (UTC)", key="time", step=3600)
        st.slider("Mission length (days)", 1, 60, key="days")
        st.slider("Mast / antenna height (m)", 1.0, 20.0, step=0.5, key="mast",
                  help="Height of the eye (solar array or antenna) above the ground.")
        site = _site(sid, ss["lat"], ss["lon"])
        landers = engine.landers()
        if not ss.get("lander") or ss["lander"] not in landers:
            ss["lander"] = site.lander if site.lander in landers else "precision_100m"
        st.selectbox("Lander preset", list(landers), format_func=lambda k: landers[k]["name"], key="lander",
                     help="Illustrative numbers unless landers.yaml cites a source.")
        st.number_input("Approach heading (°)", 0.0, 359.0, step=5.0, key="heading",
                        help="Direction of travel on final descent. Default 180° = along the meridian, toward the pole.")
        st.toggle("Assume a relay orbiter", key="relay",
                  help="Illustrative: a relay that is always reachable, so the link no longer needs Earth in view. "
                       "NASA's Artemis III requirements assume no relay.")
        st.segmented_control("View", ["Simple", "Expert"], key="mode")
    start = pd.Timestamp(dt.datetime.combine(ss["date"], ss["time"]), tz="UTC")
    sc = {"site_id": site.id, "site": site, "start": start, "days": int(ss["days"]), "mast": float(ss["mast"]),
          "lander_key": ss["lander"], "lander": engine.landers()[ss["lander"]], "heading": float(ss["heading"]),
          "expert": ss.get("mode") == "Expert", "relay": bool(ss.get("relay"))}
    qp = {"site": sid, "t": start.strftime("%Y-%m-%dT%H:%MZ"), "days": str(sc["days"]), "mast": f"{sc['mast']:g}",
          "lander": sc["lander_key"], "heading": f"{sc['heading']:g}", "mode": "expert" if sc["expert"] else "simple"}
    if sc["relay"]:
        qp["relay"] = "1"
    if sid == CUSTOM:
        qp.update(lat=f"{ss['lat']:.4f}", lon=f"{ss['lon']:.4f}")
    st.query_params.from_dict(qp)
    sc["query"] = qp
    with st.sidebar:
        with st.expander("Share this view"):
            base = (st.context.url or "").split("?")[0]
            st.code(base + "?" + "&".join(f"{k}={v}" for k, v in qp.items()), language=None, wrap_lines=True)
            st.caption("Copy the link with the button in the box. It reproduces this exact scenario.")
    return sc


def scenario() -> dict:
    """The current scenario. Under the router (Home.py) the sidebar was drawn already this run; a page run on its
    own (tests) draws it itself."""
    if st.session_state.get("_routed") and "_scenario" in st.session_state:
        return st.session_state["_scenario"]
    setup()
    sc = sidebar()
    st.session_state["_scenario"] = sc
    return sc


# --- cached computation ---

@st.cache_resource(show_spinner=False)
def _custom(lat: float, lon: float) -> engine.Site:
    return engine.custom_site(round(lat, 4), round(lon, 4))


def _site(sid: str, lat: float, lon: float) -> engine.Site:
    return _custom(lat, lon) if sid == CUSTOM else engine.load_site(sid)


@st.cache_data(show_spinner="Running the mission hour by hour...", max_entries=64)
def run(site_id: str, lat: float, lon: float, start: pd.Timestamp, days: int, mast: float, lander_key: str,
        relay: bool = False):
    site = _site(CUSTOM if site_id.startswith("custom_") else site_id, lat, lon)
    tl = engine.timeline(site, start, days, mast, engine.landers()[lander_key], relay=relay)
    return tl, scores.summary(site, tl), scores.countdowns(site, tl)


def run_sc(sc: dict):
    s = sc["site"]
    return run(s.id, s.lat, s.lon, sc["start"], sc["days"], sc["mast"], sc["lander_key"], sc["relay"])


# --- HTML pieces ---

def status_html(rating: str) -> str:
    word, ic = STATUS[rating]
    return f"<span class='g-status g-{rating}'>{icon(ic)}{word}</span>"


def card(title: str, ic: str, accent: str, rating: str, big: str, unit: str, reasons: list[str]) -> str:
    items = "".join(f"<li>{html.escape(r)}</li>" for r in reasons)
    return (f"<div class='g-card' style='--accent:{accent}'><div class='g-title'><h4>{title}</h4>{icon(ic)}</div>"
            f"{status_html(rating)}<div class='g-big'>{big}<small>{unit}</small></div><ul>{items}</ul></div>")


def chip(ic: str, accent: str, label: str, value: str, sub: str = "") -> str:
    sub = f" <span>{html.escape(sub)}</span>" if sub else ""
    return f"<div class='g-chip' style='--accent:{accent}'>{icon(ic)}{html.escape(label)} <b>{html.escape(value)}</b>{sub}</div>"


def countdown_chip(cd: dict, key: str, ic: str, accent: str, label: str) -> str:
    c = cd[key]
    if pd.isna(c["utc"]):
        return chip(ic, accent, label, "not in this window")
    spread = (c["latest"] - c["earliest"]).total_seconds() / 60
    sub = c["utc"].strftime("%-d %b %H:%M UTC") + (f", ±{spread / 2:.0f} min" if spread >= 1 else "")
    return chip(ic, accent, label, f"in {events.format_hours(c['hours'])}", sub)


def site_header(sc: dict) -> None:
    s = sc["site"]
    src = {"ldem_80s_20m+80m": "LOLA terrain, 20 m near + 80 m far", "ldem_60s_240m": "LOLA terrain, 240 m",
           "smooth_sphere": "no terrain model here: smooth-sphere horizon", "dem_80s_160m": "LOLA terrain, 160 m"}
    coarse = " <span class='g-coarse'>Coarser terrain (160 m) than catalog sites.</span>" if s.custom else ""
    st.markdown(f"# {html.escape(s.name)}")
    st.markdown(f"<div class='g-site-meta'><b>{abs(s.lat):.3f}° S, {s.lon:.3f}° E</b> &nbsp; {src.get(s.horizon_source, s.horizon_source)}"
                f" &nbsp; landing {sc['start'].strftime('%-d %b %Y %H:%M UTC')}, {sc['days']} days, "
                f"{sc['mast']:g} m mast, {html.escape(sc['lander']['name'])}{coarse}</div>", unsafe_allow_html=True)


@st.cache_data(show_spinner="Flying 200 landings across the ellipse...", max_entries=32)
def odds(site_id: str, start: pd.Timestamp, days: int, lander_key: str, relay: bool = False):
    site = engine.load_site(site_id)
    tile = engine.load_tile(site_id)
    if tile is None:
        return None
    tl = engine.timeline(site, start, days, 2.0, engine.landers()[lander_key], relay=relay)
    return landing.ellipse_odds(tile, tl, engine.landers()[lander_key])


@st.cache_data(show_spinner=False, max_entries=32)
def relief(site_id: str):
    p = engine.DERIVED / "relief" / f"{site_id}.npz"
    if not p.exists():
        return None
    with np.load(p) as z:
        return {k: z[k] for k in z.files}


@st.cache_data(show_spinner="Raising the mast...", max_entries=32)
def mast_table(site_id: str, lat: float, lon: float, start: pd.Timestamp, days: int, lander_key: str):
    site = _site(CUSTOM if site_id.startswith("custom_") else site_id, lat, lon)
    eph = engine.ephemeris(site, start, start + pd.Timedelta(days=days))
    rows = []
    for m in (1, 2, 3, 5, 7.5, 10, 12.5, 15, 20):
        tl = engine.timeline(site, start, days, m, engine.landers()[lander_key], eph=eph)
        rows.append({"mast_m": m, "pct_sunlit": 100 * tl["sunlit"].mean(), "pct_link": 100 * tl["link"].mean()})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner="Weighing ice against sunlight...", max_entries=16)
def pareto_table(site_id: str, start: pd.Timestamp, days: int, lander_key: str):
    o = odds(site_id, start, days, lander_key)
    rows = []
    if o is not None:
        p = o["points"]
        rows += [{"kind": "Landing point", "label": f"Ellipse point {i}", "psr_km": r["psr_dist_m"] / 1000,
                  "pct_both": r["pct_both"]} for i, r in p.iterrows()]
    psr = pd.read_csv(engine.DERIVED / "site_psr.csv").dropna(subset=["psr_dist_m"])
    for _, r in psr.iterrows():
        s = engine.load_site(r["site_id"])
        _, summ, _ = run(s.id, s.lat, s.lon, start, days, 2.0, lander_key)
        rows.append({"kind": "Catalog site", "label": s.name, "psr_km": r["psr_dist_m"] / 1000,
                     "pct_both": summ["pct_both"]})
    return pd.DataFrame(rows)


def dark_periods(tl: pd.DataFrame) -> pd.DataFrame:
    """Every interval with no Sun or no usable link, longest first (for blame-the-ridge)."""
    out = []
    for body, col, word in (("sun", "sunlit", "Night"), ("earth", "link", "Comms blackout")):
        w = events.windows(tl["utc"], ~tl[col].to_numpy(bool))
        for _, r in w.iterrows():
            out.append({"body": body, "what": word, "start": r["start"], "end": r["end"], "hours": max(r["duration_h"], 1)})
    df = pd.DataFrame(out)
    # nights first (that is where a ridge gets the blame), then blackouts; longest first within each
    return df.sort_values(["body", "hours"], ascending=[False, False]).reset_index(drop=True) if len(df) else df
