"""Compact map layers for the app's Map page: NASA's long-run Sun and Earth visibility (PGDA product 69, 75S map,
120 m) averaged to 2.5 km over 80-90 S, in the maps' own polar stereographic metres."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

from navigator import geo
from pipeline.horizon import AVGVISIB_DIR, AVGVISIB_MAPS, AVGVISIB_SCALE, DERIVED

MAP_NPZ = DERIVED / "map_avgvisib.npz"
CELL_M = 2500.0


def build_map_layers(cell_m: float = CELL_M) -> Path:
    base = AVGVISIB_DIR / f"{AVGVISIB_MAPS['75S']}.TIF"
    x80, _ = geo.latlon_to_xy(-80.0, 90.0, base)  # 80 S circle radius in map metres
    half = float(np.ceil(abs(x80) / cell_m) * cell_m)
    out = {}
    for body, suffix in (("sun", ""), ("earth", "_EARTH")):
        with rasterio.open(AVGVISIB_DIR / f"{AVGVISIB_MAPS['75S']}{suffix}.TIF") as ds:
            win = from_bounds(-half, -half, half, half, ds.transform)
            n = int(round(2 * half / cell_m))
            a = ds.read(1, window=win, out_shape=(n, n), resampling=Resampling.average, boundless=True,
                        fill_value=0).astype(float)
            crs = ds.crs.to_wkt()
        pct = np.clip(a * AVGVISIB_SCALE * 100, 0, 100)
        out[body] = np.rint(pct).astype(np.uint8)
    centres = -half + cell_m * (np.arange(n) + 0.5)
    np.savez_compressed(MAP_NPZ, x=centres, y=centres[::-1], sun=out["sun"], earth=out["earth"], crs=np.array(crs),
                        cell_m=cell_m, source=np.array(AVGVISIB_MAPS["75S"]))
    return MAP_NPZ


RELIEF_DIR = DERIVED / "relief"


def build_tile_relief(half_m: float = 400.0) -> list[Path]:
    """20 m LOLA heights in a square around each polar site (from the cached 20 m windows), for the landing-zone
    panel's hillshade under the ellipse points. ~40 x 40 cells, a few kB per site."""
    from pipeline.horizon import window_path
    from pipeline.sites import load_sites

    RELIEF_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for s in load_sites():
        src = window_path(s["id"], "ldem_20m")
        if not s["in_polar_dem"] or not src.exists():
            continue
        x0, y0 = geo.latlon_to_xy(s["lat"], s["lon"], src)
        with rasterio.open(src) as ds:
            win = from_bounds(x0 - half_m, y0 - half_m, x0 + half_m, y0 + half_m, ds.transform).round_offsets().round_lengths()
            z = ds.read(1, window=win, masked=True).astype(np.float32).filled(np.nan)
            t = ds.window_transform(win)
        xs = t.c + t.a * (np.arange(z.shape[1]) + 0.5)
        ys = t.f + t.e * (np.arange(z.shape[0]) + 0.5)
        p = RELIEF_DIR / f"{s['id']}.npz"
        np.savez_compressed(p, z=z, x=xs, y=ys, cell_m=abs(t.a), site_x=x0, site_y=y0)
        out.append(p)
    return out
