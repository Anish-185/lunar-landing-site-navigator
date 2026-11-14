"""Terrain horizons with the vendored NASA MMGIS HorizonProfile script, offline.

- build_coarse_dem: the 160 m DEM the app uses for custom sites (Phase 1)
- site_horizon / build_site_horizons: 720-azimuth horizon per catalog site and mast, with the occluder's location and
  name per azimuth -> data/derived/horizons/<site_id>.npz
- ellipse_points / build_tiles: 200 landing-ellipse points per site with their own horizon, slope, height error and
  PSR distance -> data/derived/tiles/<site_id>.npz
- psr distances and data/derived/psr_outlines.geojson; data/derived/lunar_features.csv (USGS names)
- shadow_snapshot: MMGIS sightmap over a 600 m window at one time (cached)
- validate_avgvisib: our long-run Sun/Earth visibility vs NASA's AVGVISIB maps
"""

from __future__ import annotations

import time
import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
DEM80 = ROOT / "data" / "raw" / "pgda90" / "LDEM_80S_80MPP_ADJ.TIF"
COARSE_DEM = ROOT / "data" / "derived" / "dem_80s_160m.tif"
INT16_NODATA = -32768


def build_coarse_dem(src: Path = DEM80, dst: Path = COARSE_DEM, factor: int = 2) -> Path:
    """Average `factor` x `factor` blocks of the 80 m LOLA DEM (factor 2 -> 160 m), round to whole metres, int16.

    Same CRS and extent as the source; tiled and DEFLATE-compressed so it stays well under 50 MB.
    """
    with rasterio.open(src) as ds:
        # Full-resolution read + NumPy block mean: an out_shape read would let GDAL use the file's overviews.
        fine = ds.read(1, masked=True).astype(np.float64).filled(np.nan)
        h, w = ds.height // factor, ds.width // factor
        transform = ds.transform @ Affine.scale(factor)
        crs = ds.crs
    blocks = fine[: h * factor, : w * factor].reshape(h, factor, w, factor)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN blocks become nodata below
        mean = np.nanmean(blocks, axis=(1, 3))
    heights = np.where(np.isfinite(mean), np.round(mean), INT16_NODATA)
    valid = heights[heights != INT16_NODATA]
    assert valid.min() > INT16_NODATA and valid.max() < 32767, "heights out of int16 range"
    dst.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dst, "w", driver="GTiff", width=w, height=h, count=1, dtype="int16", crs=crs,
                       transform=transform, nodata=INT16_NODATA, tiled=True, blockxsize=512, blockysize=512,
                       compress="deflate", predictor=2, zlevel=9) as out:
        out.write(heights.astype(np.int16), 1)
        out.update_tags(source="LDEM_80S_80MPP_ADJ.TIF (PGDA product 90)", method=f"{factor}x{factor} block average",
                        units="metres above 1737.4 km sphere")
    return dst


# --- cached 20 m windows (near field, slope, height error), shared by site horizons and ellipse points ---

WINDOW_DIR = ROOT / "data" / "raw" / "windows"
WINDOW_HALF_M = 5500.0  # ~11 km square: 5 km near field plus margin for ellipse points


def window_path(site_id: str, product: str) -> Path:
    return WINDOW_DIR / f"{site_id}_{product}.tif"


def cache_windows(site: dict, products=("ldem_20m", "ldsm_20m", "lderr_20m")) -> list[Path]:
    """Read (once) an ~11 km window of each remote 20 m product around the site into data/raw/windows/."""
    from navigator.geo import read_window
    from pipeline.fetch_data import REMOTE_20M

    WINDOW_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for product in products:
        path = window_path(site["id"], product)
        if not path.exists():
            tmp = path.with_suffix(".part.tif")
            read_window(REMOTE_20M[product], site["lat"], site["lon"], WINDOW_HALF_M, out_path=tmp)
            tmp.rename(path)
        out.append(path)
    return out


# --- site horizons ---

import pandas as pd
from joblib import Parallel, delayed

from navigator import engine, geo
from pipeline.sites import load_landers, load_sites
from vendor.mmgis_sightline import HorizonProfile as hp

DERIVED = ROOT / "data" / "derived"
HORIZON_DIR = DERIVED / "horizons"
TILE_DIR = DERIVED / "tiles"
SHADOW_DIR = DERIVED / "shadow"
FEATURES_CSV = DERIVED / "lunar_features.csv"
PSR_SHP = ROOT / "data" / "raw" / "pgda90" / "LPSR_80S_20MPP_ADJ_1km2.SHP"
PSR_GEOJSON = DERIVED / "psr_outlines.geojson"
GAZETTEER_ZIP = ROOT / "data" / "raw" / "usgs" / "MOON_nomenclature_center_pts.zip"
MASTS = (1, 2, 5, 10, 15, 20)
N_AZ = 720
NEAR_M, FAR_M = 5000.0, 200000.0
R_M = 1737400.0
ELLIPSE_N, ELLIPSE_MAST_M = 200, 2.0
COLS = ("el", "dist", "x", "y", "lat", "lon")


def _sample(path, x, y):
    with rasterio.open(path) as ds:
        v = np.array([s[0] for s in ds.sample(list(zip(np.atleast_1d(x), np.atleast_1d(y))))], dtype=float)
        if ds.nodata is not None:
            v[v == ds.nodata] = np.nan
    return v


def two_field_horizon(lat, lon, mast_m, near_dem, far_dem=DEM80, near_m=NEAR_M, far_m=FAR_M):
    """Max per azimuth of a near-field (0-near_m, near_dem) and far-field (near_m-far_m, far_dem) horizon.

    Both fields use the same eye height: the near DEM's surface + mast (the far-field call gets
    mast + z_near - z_far, since MMGIS adds the height to its own DEM's surface). Returns a dict of arrays
    (az, el, dist, x, y, lat, lon, field[0 near / 1 far]) and the surface height used.
    """
    x, y = geo.latlon_to_xy(lat, lon, near_dem)
    z_near, z_far = _sample(near_dem, x, y)[0], _sample(far_dem, x, y)[0]
    near = hp.compute_horizon_profile(str(near_dem), lat, lon, mast_m, N_AZ, near_m, 0.0, R_M)
    far = hp.compute_horizon_profile(str(far_dem), lat, lon, mast_m + (z_near - z_far), N_AZ, far_m, near_m, R_M)
    use_far = far[:, 1] > near[:, 1]
    best = np.where(use_far[:, None], far, near)
    out = {"az": near[:, 0], **{c: best[:, i + 1] for i, c in enumerate(COLS)}, "field": use_far.astype(np.int8)}
    return out, float(z_near)


def smooth_sphere_horizon(mast_m):
    """No terrain: the geometric dip of the horizon for an eye mast_m above a smooth 1737.4 km sphere."""
    dip = -np.degrees(np.arccos(R_M / (R_M + mast_m)))
    dist = np.sqrt(2 * R_M * mast_m)
    nan = np.full(N_AZ, np.nan)
    return {"az": np.arange(N_AZ) * 360.0 / N_AZ, "el": np.full(N_AZ, dip), "dist": np.full(N_AZ, dist),
            "x": nan, "y": nan, "lat": nan, "lon": nan, "field": np.full(N_AZ, -1, np.int8)}


def site_horizon(site: dict, mast_m: float) -> tuple[dict, str]:
    """Horizon for one site and mast height, plus where it came from (`horizon_source`)."""
    if site["in_polar_dem"]:
        near = window_path(site["id"], "ldem_20m")
        return two_field_horizon(site["lat"], site["lon"], mast_m, near)[0], "ldem_80s_20m+80m"
    if site["id"] == "chandrayaan_3" and window_path(site["id"], "ldem_240m").exists():
        prof = hp.compute_horizon_profile(str(window_path(site["id"], "ldem_240m")), site["lat"], site["lon"],
                                          mast_m, N_AZ, FAR_M, 0.0, R_M)
        out = {"az": prof[:, 0], **{c: prof[:, i + 1] for i, c in enumerate(COLS)}, "field": np.ones(N_AZ, np.int8)}
        return out, "ldem_60s_240m"
    return smooth_sphere_horizon(mast_m), "smooth_sphere"


def load_features():
    return pd.read_csv(FEATURES_CSV)


def build_site_horizon(site: dict) -> Path:
    features = load_features()
    per_mast, source = [], None
    for mast in MASTS:
        h, source = site_horizon(site, mast)
        h["name"], h["relation"] = geo.name_points(h["lat"], h["lon"], features)
        per_mast.append(h)
    stack = {k: np.stack([h[k] for h in per_mast]) for k in ("el", "dist", "x", "y", "lat", "lon", "field",
                                                             "name", "relation")}
    HORIZON_DIR.mkdir(parents=True, exist_ok=True)
    out = HORIZON_DIR / f"{site['id']}.npz"
    np.savez_compressed(out, az=per_mast[0]["az"], masts=np.array(MASTS, float), horizon_source=np.array(source),
                        site_lat=site["lat"], site_lon=site["lon"],
                        **{k: v.astype(np.float32) if v.dtype.kind == "f" else v for k, v in stack.items()})
    return out


def build_site_horizons(n_jobs: int = -1) -> float:
    t0 = time.time()
    Parallel(n_jobs=n_jobs)(delayed(build_site_horizon)(s) for s in load_sites())
    return time.time() - t0


def load_horizon(site_id: str) -> dict:
    with np.load(HORIZON_DIR / f"{site_id}.npz") as z:
        return {k: z[k] for k in z.files}


# --- landing-ellipse points ---

def _one_point(site_id, lat, lon):
    h, z = two_field_horizon(lat, lon, ELLIPSE_MAST_M, window_path(site_id, "ldem_20m"))
    return h, z


def ellipse_points(site: dict, lander: dict, n: int = ELLIPSE_N, seed: int = 0, n_jobs: int = -1) -> dict:
    """n Gaussian landing points (sigma = lander ellipse_sigma_m on each axis, fixed seed), each with its own
    near + far horizon at ELLIPSE_MAST_M, slope (20 m LDSM), height error (20 m) and PSR distance."""
    near = window_path(site["id"], "ldem_20m")
    x0, y0 = geo.latlon_to_xy(site["lat"], site["lon"], near)
    off = np.random.default_rng(seed).normal(0.0, lander["ellipse_sigma_m"], size=(n, 2))
    xs, ys = x0 + off[:, 0], y0 + off[:, 1]
    lats, lons = geo.xy_to_latlon(xs, ys, near)
    res = Parallel(n_jobs=n_jobs)(delayed(_one_point)(site["id"], la, lo) for la, lo in zip(lats, lons))
    features = load_features()
    names = [geo.name_points(h["lat"], h["lon"], features) for h, _ in res]
    psr = psr_distances(xs, ys)
    return {
        "x": xs, "y": ys, "lat": lats, "lon": lons, "sigma_m": lander["ellipse_sigma_m"], "mast_m": ELLIPSE_MAST_M,
        "z": np.array([z for _, z in res]),
        "slope_deg": _sample(window_path(site["id"], "ldsm_20m"), xs, ys),
        "height_err_m": _sample(window_path(site["id"], "lderr_20m"), xs, ys),
        "psr_dist_m": psr["dist_m"].to_numpy(), "psr_name": psr["name"].to_numpy().astype(str),
        "az": res[0][0]["az"],
        **{f"h_{c}": np.stack([h[c] for h, _ in res]).astype(np.float32 if c != "field" else np.int8)
           for c in COLS + ("field",)},
        "h_name": np.stack([nm for nm, _ in names]), "h_relation": np.stack([rel for _, rel in names]),
    }


def build_tiles() -> dict[str, float]:
    landers, times = load_landers(), {}
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    for site in load_sites():
        if not site["in_polar_dem"]:
            continue
        t0 = time.time()
        pts = ellipse_points(site, landers[site["lander"]])
        np.savez_compressed(TILE_DIR / f"{site['id']}.npz", lander=np.array(site["lander"]), **pts)
        times[site["id"]] = time.time() - t0
    return times


# --- PSRs ---

def _psr():
    import geopandas as gpd

    return gpd.read_file(PSR_SHP)


def psr_distances(xs, ys) -> pd.DataFrame:
    """Distance (m, polar stereographic plane) from each point to the nearest PSR > 1 km² (0 inside one)."""
    import geopandas as gpd

    psr = _psr()
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(np.atleast_1d(xs), np.atleast_1d(ys)), crs=psr.crs)
    j = gpd.sjoin_nearest(pts, psr[["name", "geometry"]], how="left", distance_col="dist_m")
    j = j[~j.index.duplicated()]  # ties: keep one
    names = j["name"].fillna("").astype(str).str.strip('"')  # the shapefile stores IDs with literal quotes
    return pd.DataFrame({"dist_m": j["dist_m"].to_numpy(), "name": names.to_numpy()})


def site_psr_table() -> pd.DataFrame:
    rows = []
    for s in load_sites():
        if s["in_polar_dem"]:
            x, y = geo.latlon_to_xy(s["lat"], s["lon"], COARSE_DEM)
            d = psr_distances([x], [y]).iloc[0]
            rows.append({"site_id": s["id"], "psr_dist_m": round(float(d["dist_m"]), 1), "psr_name": d["name"]})
        else:
            rows.append({"site_id": s["id"], "psr_dist_m": np.nan, "psr_name": ""})
    out = pd.DataFrame(rows)
    out.to_csv(DERIVED / "site_psr.csv", index=False)
    return out


def build_psr_outlines(tolerance_m: float = 40.0, max_bytes: int = 5_000_000) -> Path:
    """Simplified PSR polygons (polar stereographic metres) for the app to draw with Plotly; < 5 MB."""
    psr = _psr()[["name", "area_km2", "geometry"]].copy()
    while True:
        psr["geometry"] = _psr().geometry.simplify(tolerance_m, preserve_topology=True)
        PSR_GEOJSON.unlink(missing_ok=True)
        psr.to_file(PSR_GEOJSON, driver="GeoJSON", COORDINATE_PRECISION=0)
        if PSR_GEOJSON.stat().st_size < max_bytes:
            return PSR_GEOJSON
        tolerance_m *= 1.5


# --- USGS Gazetteer of Planetary Nomenclature -> data/derived/lunar_features.csv ---

def build_features() -> Path:
    """Approved lunar crater and mons names (centre, diameter) from the USGS Gazetteer shapefile."""
    import geopandas as gpd

    g = gpd.read_file(f"zip://{GAZETTEER_ZIP}")
    cols = {c.lower(): c for c in g.columns}
    kind = g[cols["type"]].str.lower()
    # "Satellite Feature" = lettered craters (Cabeus B, Malapert A): the names a planner looks for near the pole.
    keep = kind.str.startswith(("crater", "satellite feature", "mons"))
    out = pd.DataFrame({
        "name": g.loc[keep, cols["clean_name"] if "clean_name" in cols else cols["name"]],
        "lat": g.loc[keep, cols["center_lat"]].astype(float),
        "lon": (g.loc[keep, cols["center_lon"]].astype(float) + 180) % 360 - 180,
        "diameter_km": g.loc[keep, cols["diameter"]].astype(float),
        "kind": np.where(kind[keep].str.startswith("mons"), "mons", "crater"),
    })
    out = out[out["diameter_km"] > 0].sort_values(["lat", "name"])
    out.to_csv(FEATURES_CSV, index=False, float_format="%.4f")
    return FEATURES_CSV


# --- shadow snapshot (MMGIS sightmap) ---

def shadow_snapshot(site: dict, utc, half_m: float = 300.0, target: str = "SUN") -> dict:
    """Lit/shadow grid over a 600 m square around the site at one UTC time (cached in data/derived/shadow/).

    Local shadows come from MMGIS sightmap on the site's 20 m window (terrain within ~5 km). Terrain farther away is
    taken from the site's far-field horizon: if the source is below it, the whole window is in shadow.
    """
    from vendor.mmgis_sightline import sightmap as sm

    t = pd.Timestamp(utc).tz_convert("UTC") if pd.Timestamp(utc).tzinfo else pd.Timestamp(utc, tz="UTC")
    out = SHADOW_DIR / f"{site['id']}_{target.lower()}_{t.strftime('%Y%m%dT%H%M%SZ')}.npz"
    if out.exists():
        with np.load(out) as z:
            return {k: z[k] for k in z.files}
    dem = window_path(site["id"], "ldem_20m")
    x, y = geo.latlon_to_xy(site["lat"], site["lon"], dem)
    res = sm.sightmap(dem, site["lat"], site["lon"], ELLIPSE_MAST_M, target, t,
                      viewport_bounds=[x - half_m, y - half_m, x + half_m, y + half_m], shadow_reach_m=NEAR_M)
    hz = load_horizon(site["id"])
    far = np.where(hz["field"][1] == 1, hz["el"][1], -90.0)  # mast 2 m row
    blocked_far = res["el"] < np.interp(res["az"], hz["az"], far, period=360.0)
    grid = np.where(blocked_far & (res["grid"] != 9), 0, res["grid"]).astype(np.uint8)
    snap = {"grid": grid, "az": res["az"], "el": res["el"], "blocked_far": blocked_far,
            "bounds_xy": np.array([x - half_m, y - half_m, x + half_m, y + half_m]), "utc": np.array(t.isoformat())}
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **snap)
    return snap


# --- validation against NASA's long-run visibility maps (PGDA product 69) ---

AVGVISIB_DIR = ROOT / "data" / "raw" / "pgda69"
AVGVISIB_MAPS = {"85S": "AVGVISIB_85S_060M_201608", "75S": "AVGVISIB_75S_120M_201608"}
AVGVISIB_SCALE = 4e-5
# The label and product page give no exact averaging window, only "hourly timesteps spanning 18.6 years" (one
# lunar nutation cycle). We use the 18.6 years ending at the product date (Aug 2016), 6-hourly.
AVGVISIB_PERIOD = ("1998-01-01", "2016-08-01")
VALIDATION_MAST_M = 1.0
AVGVISIB_CSV = DERIVED / "validation_avgvisib.csv"


def _visible_fractions(site: dict, times: pd.DatetimeIndex) -> dict:
    eph = engine.sun_earth_azel(site["lat"], site["lon"], times)
    hz = load_horizon(site["id"])
    el_h = hz["el"][list(hz["masts"]).index(VALIDATION_MAST_M)]
    out = {}
    for body, radius in (("sun", engine.sun_radius_deg), ("earth", engine.earth_radius_deg)):
        h = np.interp(eph[f"{body}_az"], hz["az"], el_h, period=360.0)
        el = eph[f"{body}_el"].to_numpy()
        out[f"our_{body}_point"] = float(np.mean(el > h))
        out[f"our_{body}_disc"] = float(np.mean(el + radius(eph[f"{body}_range_km"]) > h))  # any part of the disc
    return out


def validate_avgvisib(n_jobs: int = -1) -> pd.DataFrame:
    """Our long-run Sun/Earth visible fractions vs NASA AVGVISIB at every polar catalog site.

    NASA's maps count a timestep as visible when any part of the disc is above the horizon (PDS label), so
    `*_disc` is the like-for-like number; `*_point` treats the Sun/Earth as a point (disc centre)."""
    times = pd.date_range(*AVGVISIB_PERIOD, freq="6h", tz="UTC", inclusive="left")
    sites = [s for s in load_sites() if s["in_polar_dem"]]
    ours = Parallel(n_jobs=n_jobs)(delayed(_visible_fractions)(s, times) for s in sites)
    rows = []
    for s, o in zip(sites, ours):
        grid = "85S" if s["lat"] <= -85.0 else "75S"
        nasa = {}
        for body, suffix in (("sun", ""), ("earth", "_EARTH")):
            path = AVGVISIB_DIR / f"{AVGVISIB_MAPS[grid]}{suffix}.TIF"
            x, y = geo.latlon_to_xy(s["lat"], s["lon"], path)
            nasa[f"nasa_{body}"] = float(_sample(path, x, y)[0]) * AVGVISIB_SCALE
        row = {"site_id": s["id"], "nasa_map": AVGVISIB_MAPS[grid], **nasa, **o}
        for body in ("sun", "earth"):
            row[f"diff_{body}"] = row[f"our_{body}_disc"] - row[f"nasa_{body}"]
        row["flag_over_10pct"] = bool(max(abs(row["diff_sun"]), abs(row["diff_earth"])) > 0.10)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(AVGVISIB_CSV, index=False, float_format="%.4f")
    return df
