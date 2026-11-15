"""Mission summary for one scenario, with plain-English reasons that name the terrain to blame."""

from __future__ import annotations

import numpy as np
import pandas as pd

from navigator import engine, events, geo, power

# A terrain reason is given only when the terrain is what hides the body (horizon above the smooth-sphere dip).
TERRAIN_MARGIN_DEG = 0.05


def _when(t) -> str:
    return pd.Timestamp(t).strftime("%-d %b %H:%M UTC")


def blame_at(site: engine.Site, mast_m: float, body: str, az: float, el: float, when=None) -> str:
    """Why `body` is hidden at azimuth `az`: the named occluder from the site's horizon, or the Sun/Earth simply
    being below the horizon."""
    j = site.mast_row(mast_m)
    k = int(np.rint((az % 360.0) / (360.0 / len(site.az)))) % len(site.az)
    h = float(site.horizon(mast_m)[k])
    label = body.capitalize()
    suffix = f" from {_when(when)}" if when is not None else ""
    if not site.has_terrain or h <= TERRAIN_MARGIN_DEG or el < -2.0:
        return f"{label} below the horizon (el {el:.1f}°){suffix}"
    return geo.blame_line(label, str(site.occ_name[j, k]), str(site.occ_relation[j, k]),
                          float(site.dist[j, k]), float(site.az[k])) + suffix


def _dark_reason(site, tl, body: str, mask_col: str, word: str) -> tuple[dict, str | None]:
    dark = ~tl[mask_col].to_numpy(bool)
    run = events.longest(tl["utc"], dark)
    if run["hours"] == 0:
        return run, None
    i = min(int(pd.DatetimeIndex(tl["utc"]).searchsorted(run["start"])), len(tl) - 1)
    r = tl.iloc[i]
    if body == "earth" and r["earth_clear"] > 0:
        why = (f"Earth only {r['earth_clear']:.1f}° above the terrain (multipath risk) from {_when(r['utc'])}"
               if r["dsn"] else f"No DSN complex sees the Moon from {_when(r['utc'])}")
    else:
        why = blame_at(site, tl.attrs["mast_m"], body, float(r[f"{body}_az"]), float(r[f"{body}_el"]), r["utc"])
    return run, f"Longest {word}: {run['hours']:.0f} h. {why}."


def summary(site: engine.Site, tl: pd.DataFrame) -> dict:
    """% sunlit / link / both, longest night and blackout (h), battery survival, eclipses, and reasons."""
    lander = tl.attrs["lander"]
    bat = power.battery(tl["utc"], tl["power_W"], lander["load_W"], lander["battery_Wh"])
    night, night_why = _dark_reason(site, tl, "sun", "sunlit", "night")
    black, black_why = _dark_reason(site, tl, "earth", "link", "comms blackout")
    ecl = events.windows(tl["utc"], (tl["eclipse"] > 0) & (tl["sun_frac"] > 0))
    reasons = []
    pct = {k: 100.0 * float(tl[c].mean()) for k, c in (("sunlit", "sunlit"), ("link", "link"), ("both", "both"))}
    reasons.append(f"Sunlit {pct['sunlit']:.0f}% of the mission.")
    if night_why:
        reasons.append(night_why)
    reasons.append(f"Direct-to-Earth link usable {pct['link']:.0f}% of the time "
                   f"(Earth clear by ≥ 2° and a DSN dish in view).")
    if black_why:
        reasons.append(black_why)
    low = float(((tl["band"] == "poor") & tl["earth_visible"]).mean() * 100)
    if low >= 5:
        reasons.append(f"Earth skims the terrain (0–2° clear, multipath risk) {low:.0f}% of the time.")
    if bat["survives"]:
        reasons.append(f"Battery never drops below {power.FLOOR:.0%} (lowest {bat['min_soc']:.0%}).")
    else:
        reasons.append(f"Battery falls below {power.FLOOR:.0%} on {_when(bat['first_below'])} "
                       f"({lander['load_W']:.0f} W load, {lander['battery_Wh']:.0f} Wh).")
    for _, e in ecl.iterrows():
        depth = tl.loc[(tl["utc"] >= e["start"]) & (tl["utc"] <= e["end"]), "eclipse"].max()
        reasons.append(f"Earth eclipses the Sun from {_when(e['start'])} for {max(e['duration_h'], 1):.0f} h "
                       f"(up to {depth:.0%} of the disc).")
    return {
        "pct_sunlit": pct["sunlit"], "pct_link": pct["link"], "pct_both": pct["both"],
        "longest_night_h": night["hours"], "longest_night_start": night["start"],
        "longest_blackout_h": black["hours"], "longest_blackout_start": black["start"],
        "survives": bool(bat["survives"]), "min_soc": float(bat["min_soc"]), "first_below": bat["first_below"],
        "eclipses": len(ecl), "reasons": reasons,
    }


def verdict(s: dict) -> dict:
    """Traffic-light cards (always icon + word + colour): Power and Comms."""
    p = ("good" if s["survives"] and s["pct_sunlit"] >= 60 else "caution" if s["survives"] else "bad")
    c = ("good" if s["pct_link"] >= 60 else "caution" if s["pct_link"] >= 25 else "bad")
    return {"power": p, "comms": c}


DEFAULT_SIGMA_Z_M = {"catalog": 1.0, "custom": 10.0}  # illustrative fallbacks (docs/METHOD.md)


def sigma_z(site: engine.Site) -> float:
    """Terrain height uncertainty (m) used for countdown windows: the 95th percentile of the LOLA 20 m height-error
    map over the site's landing ellipse when there is a tile, else an illustrative 1 m (catalog) or 10 m (custom
    sites on the 160 m DEM, which smooths ridges)."""
    tile = None if site.custom else engine.load_tile(site.id)
    if tile is not None and np.isfinite(tile["height_err_m"]).any():
        return float(max(np.nanpercentile(tile["height_err_m"], 95), 0.1))
    return DEFAULT_SIGMA_Z_M["custom" if site.custom else "catalog"]


def countdowns(site: engine.Site, tl: pd.DataFrame, now=None) -> dict:
    """Next sunset/sunrise/Earthset/Earthrise after `now` (default: start of the timeline), each with an
    earliest-latest window from the horizon height uncertainty atan(sigma_z / occluder distance)."""
    from navigator import visibility

    now = tl["utc"].iloc[0] if now is None else pd.Timestamp(now)
    j, sz = site.mast_row(tl.attrs["mast_m"]), sigma_z(site)
    out = {}
    for body, word in (("sun", "sun"), ("earth", "earth")):
        dist = site.dist[j][tl[f"{body}_occ"].to_numpy()]
        sig = visibility.horizon_sigma_deg(dist, sz) if site.has_terrain else 0.0
        for kind, label in (("set", f"{word}set"), ("rise", f"{word}rise")):
            out[label] = events.countdown(tl["utc"], tl[f"{body}_clear"], now, kind, sigma=sig)
    out["sigma_z_m"] = sz
    return out
