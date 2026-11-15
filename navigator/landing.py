"""Touchdown lighting and landing-zone odds over the precomputed landing-ellipse points (pure NumPy, no GDAL).

Each tile (data/derived/tiles/<site>.npz) holds 200 Gaussian landing points, each with its own 720-azimuth horizon
at 2 m, 20 m slope and distance to the nearest PSR. The Sun/Earth directions are taken from the site's ephemeris:
over a ~100 m ellipse they change by < 0.01 deg.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from navigator import comms, eclipse, power, visibility

MAX_SLOPE_DEG = 10.0  # NASA: surface slope for landing (100 m baseline) < 10 deg (docs/METHOD.md)
DEFAULT_HEADING = 180.0  # descent along the local meridian, toward the pole
CAMERA_CONE_DEG, CAMERA_LOW_SUN_DEG = 30.0, 10.0
MIN_LINK_PCT = 50.0  # illustrative: the link must be usable at least half the mission


def angle_diff(a, b):
    """Smallest absolute difference between two azimuths (deg, 0-180)."""
    return np.abs((np.asarray(a, float) - np.asarray(b, float) + 180.0) % 360.0 - 180.0)


def landing_light(tile: dict | None, sun_az: float, sun_el: float, approach_heading: float = DEFAULT_HEADING,
                  site_horizon: np.ndarray | None = None, az_grid: np.ndarray | None = None) -> dict:
    """Lighting at touchdown: Sun elevation, Sun vs approach heading ('sun in camera' when within 30 deg of the
    heading and below 10 deg), % of the landing zone in shadow (share of the ellipse points whose own horizon at
    the Sun's azimuth is above the Sun's elevation), and the shadow length of a 1 m boulder (1 / tan el).

    Without a tile (custom sites) the site's own horizon gives 0 % or 100 %."""
    if tile is not None:
        h = visibility.horizon_at(tile["az"], tile["h_el"], [sun_az])[:, 0]
    else:
        h = np.array([visibility.horizon_at(az_grid, site_horizon, sun_az)])
    shadow_pct = 100.0 * float(np.mean(h > sun_el))
    delta = float(angle_diff(sun_az, approach_heading))
    in_camera = delta < CAMERA_CONE_DEG and sun_el < CAMERA_LOW_SUN_DEG
    boulder = 1.0 / np.tan(np.radians(sun_el)) if sun_el > 0 else np.inf
    reasons, rating = [], "good"
    if sun_el <= 0 or shadow_pct >= 50:
        rating = "bad"
    elif in_camera or shadow_pct >= 10 or sun_el < 1.0:
        rating = "caution"
    reasons.append(f"Sun {sun_el:.1f}° up at az {sun_az:.0f}°." if sun_el > 0 else
                   f"Sun below the horizon ({sun_el:.1f}°): no light to land by.")
    reasons.append(f"{shadow_pct:.0f}% of the landing zone is in terrain shadow.")
    if in_camera:
        reasons.append(f"Sun in the camera: only {delta:.0f}° off the approach heading ({approach_heading:.0f}°).")
    else:
        reasons.append(f"Sun {delta:.0f}° off the approach heading ({approach_heading:.0f}°): out of the camera.")
    if np.isfinite(boulder):
        reasons.append(f"A 1 m boulder casts a {boulder:.0f} m shadow.")
    return {"rating": rating, "sun_el": float(sun_el), "sun_az": float(sun_az), "delta_heading": delta,
            "sun_in_camera": bool(in_camera), "shadow_pct": shadow_pct, "boulder_shadow_m": float(boulder),
            "reasons": reasons}


def ellipse_odds(tile: dict, tl: pd.DataFrame, lander: dict, max_slope: float = MAX_SLOPE_DEG,
                 min_link_pct: float = MIN_LINK_PCT, thresholds: dict | None = None) -> dict:
    """Run the mission at every landing point of the tile against the site timeline `tl` (engine.timeline).

    Criteria per point: slope <= max_slope; battery stays above the floor; link usable >= min_link_pct of the time;
    Sun visible at touchdown. Returns P(all pass), per-criterion pass rates and a per-point table."""
    az = tile["az"]
    out = {}
    for body in ("sun", "earth"):
        h = visibility.horizon_at(az, tile["h_el"], tl[f"{body}_az"].to_numpy())  # (n, T)
        clear = tl[f"{body}_el"].to_numpy()[None, :] - h
        out[body] = visibility.disc_fraction(clear, tl[f"{body}_r"].to_numpy()[None, :])
        out[f"{body}_clear"] = clear
    eff = eclipse.effective_sun(out["sun"], tl["eclipse"].to_numpy()[None, :])
    pw = power.array_power(tl["sun_el"].to_numpy()[None, :], eff, lander["array_W"], lander["panel"])
    bat = power.battery(tl["utc"], pw, lander["load_W"], lander["battery_Wh"])
    link = comms.link_usable(comms.band(out["earth_clear"], thresholds), tl["dsn"].to_numpy()[None, :])
    if tl.attrs.get("relay"):
        link = np.ones_like(link, dtype=bool)
    pts = pd.DataFrame({
        "x": tile["x"], "y": tile["y"], "lat": tile["lat"], "lon": tile["lon"], "slope_deg": tile["slope_deg"],
        "psr_dist_m": tile["psr_dist_m"],
        "pct_sunlit": 100 * (eff > 0).mean(axis=1), "pct_link": 100 * link.mean(axis=1),
        "pct_both": 100 * ((eff > 0) & link).mean(axis=1), "min_soc": bat["min_soc"],
    })
    pts["pass_slope"] = pts["slope_deg"] <= max_slope
    pts["pass_power"] = bat["survives"]
    pts["pass_comms"] = pts["pct_link"] >= min_link_pct
    pts["pass_light"] = eff[:, 0] > 0
    crit = ["pass_slope", "pass_power", "pass_comms", "pass_light"]
    pts["pass_all"] = pts[crit].all(axis=1)
    return {"p_success": float(pts["pass_all"].mean()), "rates": {c[5:]: float(pts[c].mean()) for c in crit},
            "points": pts, "n": len(pts), "max_slope": max_slope, "min_link_pct": min_link_pct}
