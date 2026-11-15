"""Slip Replanner: when the launch slips, re-rank every site x landing date and propose Plan B.

Landing date = launch + cruise + slip. For each site the hourly visibility is computed once over the whole span
(engine.timeline), then every candidate landing date is a window into it: % both via cumulative sums and battery
survival for all dates at once (power.battery over a (n_dates, mission_hours) matrix).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from navigator import engine, power, scores


def landing_date(launch, cruise_days: float, slip_days: float) -> pd.Timestamp:
    t = pd.Timestamp(launch)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return (t + pd.Timedelta(days=cruise_days + slip_days)).round("1h")


def candidate_sites() -> list[str]:
    """Catalog sites with terrain horizons, excluding the flown-mission duplicates (IM-2 target)."""
    return [s["id"] for s in engine.catalog() if s["in_polar_dem"] and s["id"] != "im2_target"]


def grid(site_ids, center, lander: dict, days: int, span_days: int = 60, step_days: int = 1,
         mast_m: float = 2.0) -> pd.DataFrame:
    """% both (sunlit and link usable), % sunlit, % link and battery survival for every site and landing date in
    center +/- span_days. One row per (site, date)."""
    center = pd.Timestamp(center).floor("1h")
    dates = pd.date_range(center - pd.Timedelta(days=span_days), center + pd.Timedelta(days=span_days),
                          freq=f"{step_days}D")
    hours = int(days * 24)
    rows = []
    for sid in site_ids:
        site = engine.load_site(sid)
        tl = engine.timeline(site, dates[0], (dates[-1] - dates[0]).days + days + 1, mast_m, lander)
        idx = np.asarray((dates - dates[0]) / pd.Timedelta(hours=1)).astype(int)
        win = idx[:, None] + np.arange(hours)[None, :]
        win = np.clip(win, 0, len(tl) - 1)
        sun = tl["sunlit"].to_numpy()[win]
        link = tl["link"].to_numpy()[win]
        bat = power.battery(tl["utc"].iloc[:hours], tl["power_W"].to_numpy()[win], lander["load_W"],
                            lander["battery_Wh"])
        first = bat["first_below"]
        for k, d in enumerate(dates):
            fb = first[k]
            rows.append({"site_id": sid, "name": site.name, "date": d, "pct_both": 100 * float((sun[k] & link[k]).mean()),
                         "pct_sunlit": 100 * float(sun[k].mean()), "pct_link": 100 * float(link[k].mean()),
                         "survives": bool(bat["survives"][k]),
                         "fails_after_h": np.nan if pd.isna(fb) else (fb - tl["utc"].iloc[0]).total_seconds() / 3600})
    return pd.DataFrame(rows)


def score(df: pd.DataFrame) -> pd.Series:
    """Ranking key: % both, with battery failure pushed below every surviving option."""
    return df["pct_both"] - 1000.0 * (~df["survives"])


def plan_b(df: pd.DataFrame, site_id: str, date) -> dict:
    """Original plan and the top alternatives: other site same date, same site later date, best overall.
    A slipped launch cannot land earlier, so the date alternatives only look at or after the slipped date; ties go
    to the earliest date."""
    date = pd.Timestamp(date)
    d = df.assign(rank=score(df))
    same_date = d[d["date"] == d.loc[(d["date"] - date).abs().idxmin(), "date"]]
    orig = same_date[same_date["site_id"] == site_id].iloc[0]
    other_site = same_date[same_date["site_id"] != site_id].sort_values("rank", ascending=False).iloc[0]
    later = d[d["date"] >= orig["date"]]
    same_site = later[(later["site_id"] == site_id) & (later["date"] != orig["date"])]
    same_site = same_site.sort_values(["rank", "date"], ascending=[False, True]).iloc[0] if len(same_site) else orig
    best = later.sort_values(["rank", "date"], ascending=[False, True]).iloc[0]
    return {"original": orig, "other_site": other_site, "same_site": same_site, "best": best}


def what_changed(a: dict, b: dict) -> list[str]:
    """Plain-English differences between two scores.summary results (a = original, b = alternative)."""
    out = []
    if a["survives"] != b["survives"]:
        out.append("battery now survives" if b["survives"] else "battery now fails")
    for key, label, unit, better_low in (("longest_night_h", "longest night", "h", True),
                                         ("longest_blackout_h", "longest blackout", "h", True),
                                         ("pct_sunlit", "sunlit", "%", False), ("pct_link", "link", "%", False)):
        da, db = a[key], b[key]
        if abs(db - da) >= (6 if unit == "h" else 5):
            out.append(f"{label} {da:.0f} → {db:.0f} {unit}")
    if a.get("eclipses", 0) != b.get("eclipses", 0):
        out.append("avoids the eclipse" if b["eclipses"] < a["eclipses"] else "adds an eclipse")
    return out or ["about the same"]


def explain(site_id: str, date, lander: dict, days: int, mast_m: float = 2.0) -> dict:
    site = engine.load_site(site_id)
    tl = engine.timeline(site, date, days, mast_m, lander)
    return scores.summary(site, tl)
