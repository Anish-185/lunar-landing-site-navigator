"""Export the real data behind the story site (site/public/data/story.json) and the few shadow snapshots it and the
Athena replay need. Every number on the story site comes from here."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import yaml

from navigator import engine, geo, landing, replan, scores
from pipeline.horizon import AVGVISIB_DIR, AVGVISIB_MAPS, AVGVISIB_SCALE, DERIVED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "public" / "data" / "story.json"
RIM_SITE, RIM_START, RIM_DAYS = "artemis_de_gerlache_rim_2", "2027-01-01T00:00Z", 30
RIDGE_SITE, RIDGE_HALF_M = "blue_moon_mk1_target", 900.0
ATHENA_UTC = "2025-03-06T17:28:50Z"
SLIP_SITE, SLIP_PLANNED, SLIP_DAYS, SLIP_MISSION = "artemis_nobile_rim_2", "2027-01-12T12:00Z", 42, 7
SNAPSHOTS = [("im2_actual", ATHENA_UTC)]


def build_shadow_snapshots() -> list[str]:
    """MMGIS sightmap snapshots used by the story and the Athena replay (cached; needs GDAL + Numba)."""
    from pipeline.horizon import shadow_snapshot
    from pipeline.sites import site_by_id

    for sid, utc in SNAPSHOTS:
        shadow_snapshot(site_by_id(sid), utc)
    return [f"{s}@{u}" for s, u in SNAPSHOTS]


def _r(a, nd=2):
    return np.round(np.asarray(a, float), nd).tolist()


def _segments(site, mast_m: float = 2.0) -> list[dict]:
    """Runs of azimuth with the same named occluder, for labelling the skyline."""
    j = site.mast_row(mast_m)
    names, dist = site.occ_name[j], site.dist[j]
    out, k = [], 0
    while k < len(names):
        e = k
        while e + 1 < len(names) and names[e + 1] == names[k]:
            e += 1
        if names[k] and (e - k) >= 6:
            out.append({"name": str(names[k]), "az0": float(site.az[k]), "az1": float(site.az[e]),
                        "km": round(float(np.median(dist[k:e + 1])) / 1000, 1)})
        k = e + 1
    return out


def sun_circles() -> dict:
    site = engine.load_site(RIM_SITE)
    tl = engine.timeline(site, RIM_START, RIM_DAYS, 2.0)
    h = site.horizon(2.0)
    blocks = []
    for _, w in scores.events.windows(tl["utc"], ~tl["sunlit"].to_numpy()).iterrows():
        i = min(int(pd.DatetimeIndex(tl["utc"]).searchsorted(w["start"])), len(tl) - 1)
        r = tl.iloc[i]
        blocks.append({"start": w["start"].isoformat(), "hours": round(float(w["duration_h"])), "az": round(float(r["sun_az"]), 1),
                       "why": scores.blame_at(site, 2.0, "sun", float(r["sun_az"]), float(r["sun_el"]))})
    step = 3  # every 3 h is plenty for a 30-day path
    return {"site": site.name, "lat": site.lat, "lon": site.lon, "start": RIM_START, "days": RIM_DAYS,
            "az": _r(site.az, 1), "horizon": _r(h), "segments": _segments(site),
            "sun_az": _r(tl["sun_az"].iloc[::step], 2), "sun_el": _r(tl["sun_el"].iloc[::step], 3),
            "sun_r": round(float(tl["sun_r"].mean()), 3), "t": [t.isoformat() for t in tl["utc"].iloc[::step]],
            "sunlit": tl["sunlit"].iloc[::step].astype(int).tolist(), "pct_sunlit": round(100 * float(tl["sunlit"].mean()), 1),
            "blocks": blocks}


def earth_bobs() -> dict:
    site = engine.load_site(RIM_SITE)
    tl = engine.timeline(site, RIM_START, RIM_DAYS, 2.0)
    s = tl.iloc[::2]
    return {"site": site.name, "t": [t.isoformat() for t in s["utc"]], "earth_el": _r(s["earth_el"], 3),
            "earth_h": _r(s["earth_h"], 3), "earth_az": _r(s["earth_az"], 1), "visible": s["earth_visible"].astype(int).tolist(),
            "pct_visible": round(100 * float(tl["earth_visible"].mean()), 1),
            "range": [round(float(tl["earth_el"].min()), 2), round(float(tl["earth_el"].max()), 2)]}


def small_moves() -> dict:
    """NASA's own AVGVISIB (85S, 60 m) around the Blue Moon MK1 ridge site, plus our value."""
    site = engine.load_site(RIDGE_SITE)
    path = AVGVISIB_DIR / f"{AVGVISIB_MAPS['85S']}.TIF"
    with rasterio.open(path) as ds:
        x, y = geo.latlon_to_xy(site.lat, site.lon, path)
        r, c = ds.index(x, y)
        k = int(RIDGE_HALF_M // abs(ds.transform.a))
        a = ds.read(1, window=rasterio.windows.Window(c - k, r - k, 2 * k + 1, 2 * k + 1)).astype(float) * AVGVISIB_SCALE * 100
        cell = abs(ds.transform.a)
    rng = pd.read_csv(DERIVED / "validation_avgvisib_range.csv").set_index("site_id").loc[RIDGE_SITE]
    off = (np.arange(2 * k + 1) - k) * cell
    hz = engine.load_site(RIDGE_SITE)
    return {"site": site.name, "cell_m": cell, "x": _r(off, 0), "y": _r(off[::-1], 0), "pct": _r(a, 1),
            "nasa_here": round(100 * float(rng["nasa_sun"]), 1), "nasa_min": round(100 * float(rng["nasa_sun_min"]), 1),
            "nasa_max": round(100 * float(rng["nasa_sun_max"]), 1), "ours": round(100 * float(rng["our_sun"]), 1),
            "radius_m": float(rng["radius_m"]), "horizon_source": hz.horizon_source}


def athena() -> dict:
    act, tgt = engine.load_site("im2_actual"), engine.load_site("im2_target")
    nova = engine.landers()["nova_c"]
    t0 = pd.Timestamp(ATHENA_UTC)
    eph = engine.sun_earth_azel(act.lat, act.lon, [t0]).iloc[0]
    tile = engine.load_tile("im2_actual")
    light = landing.landing_light(tile, float(eph["sun_az"]), float(eph["sun_el"]))
    tl = engine.timeline(tgt, t0.floor("1h"), 10, 2.0, nova)
    odds = landing.ellipse_odds(engine.load_tile("im2_target"), tl, nova)
    with np.load(DERIVED / "relief" / "im2_actual.npz") as z:
        rel = {k: z[k] for k in z.files}
    from navigator.plots import hillshade

    hs = hillshade(rel["z"], float(rel["cell_m"]), az_deg=float(eph["sun_az"]), alt_deg=12)
    sx, sy = float(rel["site_x"]), float(rel["site_y"])
    tx, ty = geo.latlon_to_xy(tgt.lat, tgt.lon, engine.COARSE_DEM)
    pts = landing.ellipse_odds(tile, engine.timeline(act, t0.floor("1h"), 10, 2.0, nova), nova)["points"]
    snap = np.load(DERIVED / "shadow" / "im2_actual_sun_20250306T172850Z.npz")
    depth = np.array([0.1, 0.2]) * 20
    return {"utc": ATHENA_UTC, "sun_el": round(light["sun_el"], 2), "sun_az": round(light["sun_az"], 1),
            "boulder_m": round(light["boulder_shadow_m"]), "shadow_pct": light["shadow_pct"], "rating": light["rating"],
            "p_success_target": round(100 * odds["p_success"]), "reported_miss_m": 250,
            "lroc_miss_m": round(float(geo.great_circle_m(act.lat, act.lon, tgt.lat, tgt.lon))),
            "crater_m": 20, "crater_shadow_m": _r(depth / np.tan(np.radians(light["sun_el"])), 0),
            "relief": {"x": _r(rel["x"] - sx, 0), "y": _r(rel["y"] - sy, 0), "shade": _r(hs, 2)},
            "target": [round(tx - sx), round(ty - sy)],
            "points": {"x": _r(pts["x"] - sx, 1), "y": _r(pts["y"] - sy, 1)},
            "snapshot_lit_pct": round(100 * float((snap["grid"] == 1).mean()), 1)}


def slip() -> dict:
    lander = engine.landers()["precision_100m"]
    planned = pd.Timestamp(SLIP_PLANNED)
    center = planned + pd.Timedelta(days=45)
    df = replan.grid(replan.candidate_sites(), center, lander, SLIP_MISSION, span_days=60, step_days=1)
    names = list(dict.fromkeys(df["name"]))
    dates = sorted(df["date"].unique())
    piv = df.pivot_table(index="name", columns="date", values="pct_both", sort=False).reindex(names)
    surv = df.pivot_table(index="name", columns="date", values="survives", sort=False).reindex(names)
    return {"site": engine.load_site(SLIP_SITE).name, "planned": planned.isoformat(), "slip_days": SLIP_DAYS,
            "names": names, "dates": [pd.Timestamp(d).isoformat() for d in dates], "pct_both": _r(piv.values, 0),
            "survives": surv.values.astype(int).tolist(), "mission_days": SLIP_MISSION, "lander": lander["name"]}


def evidence() -> dict:
    hz = pd.read_csv(DERIVED / "validation_horizons.csv")
    rng = pd.read_csv(DERIVED / "validation_avgvisib_range.csv")
    names = {s["id"]: s["name"] for s in engine.catalog()}
    hind = []
    for m in yaml.safe_load((ROOT / "pipeline" / "hindcast.yaml").read_text())["missions"]:
        ss = scores.first_sunset(engine.load_site(m["site_id"]), m["landing_utc"])
        hind.append({"name": m["name"], "landed": m["landing_utc"], "our_sunset": ss.isoformat() if pd.notna(ss) else None,
                     "reported": m["reported_end"], "ended_by": m["ended_by"], "source": m["source_url"]})
    return {"horizons_max_arcsec": round(float(hz["sep"].max()) * 3600, 4), "horizons_n": int(len(hz)),
            "sun_in_range": int(rng["sun_in_range"].sum()), "earth_in_range": int(rng["earth_in_range"].sum()),
            "n_sites": int(len(rng)),
            "table": [{"site": names[r["site_id"]], "nasa": round(100 * r["nasa_sun"], 1), "ours": round(100 * r["our_sun"], 1),
                       "min": round(100 * r["nasa_sun_min"], 1), "max": round(100 * r["nasa_sun_max"], 1),
                       "inside": bool(r["sun_in_range"])} for _, r in rng.iterrows()],
            "hindcast": hind}


def pole() -> dict:
    """Catalog sites in the hillshade's frame (polar stereographic km) and the hillshade's extent."""
    with rasterio.open(engine.COARSE_DEM) as ds:
        b = ds.bounds
    sites = []
    for s in engine.catalog():
        if s["lat"] <= -80 and s["id"] != "im2_target":
            x, y = geo.latlon_to_xy(s["lat"], s["lon"], engine.COARSE_DEM)
            short = s["name"].split(" (")[0].replace("Peak near ", "").replace(" target", "")
            sites.append({"id": s["id"], "name": short, "x_km": round(x / 1000, 2), "y_km": round(y / 1000, 2)})
    return {"extent_km": [round(b.left / 1000, 2), round(b.bottom / 1000, 2), round(b.right / 1000, 2), round(b.top / 1000, 2)],
            "sites": sites}


def build_story_data() -> Path:
    data = {"generated": pd.Timestamp.now(tz="UTC").isoformat(), "pole": pole(), "sun": sun_circles(), "earth": earth_bobs(),
            "ridge": small_moves(), "athena": athena(), "slip": slip(), "evidence": evidence()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
    return OUT


if __name__ == "__main__":
    p = build_story_data()
    print(p, f"{p.stat().st_size / 1e3:.0f} kB")
