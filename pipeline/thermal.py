"""Measured thermal layer (Phase 9): Diviner Polar Resource Product, south (Paige et al. 2010).

DLRE_PRP_SOUTH.TAB (PDS, LRO-L-DLRE-5-PRP-V2.0): one row per triangle of a south polar mesh, with its centre
lat/lon, annual average and maximum surface temperature (K) and the depth below which water ice would be stable (m).
We keep 80-90 S, project the centres to our polar stereographic CRS and
- average them onto a 1 km grid for the Map page (data/derived/thermal_south.npz), and
- average the triangles within 500 m of each catalog site (data/derived/site_thermal.csv).
Cold trap: annual maximum below 110 K (where water ice is stable at the surface; Paige et al. 2010).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from navigator import engine, geo
from pipeline.fetch_data import download
from pipeline.sites import load_sites

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "diviner"
BASE = "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
FILES = {"dlre_prp_south.lbl": "data_derived_prp/dlre_prp_south.lbl", "dlre_prp.fmt": "label/dlre_prp.fmt",
         "dlre_prp_south.tab": "data_derived_prp/dlre_prp_south.tab"}
GRID_NPZ = engine.DERIVED / "thermal_south.npz"
SITE_CSV = engine.DERIVED / "site_thermal.csv"
COLD_TRAP_K = 110.0
CELL_M = 1000.0
SITE_RADIUS_M = 500.0
# 0-based [start, end) byte ranges from dlre_prp.fmt (START_BYTE is 1-based)
COLSPECS = {"lon": (126, 141), "lat": (143, 158), "tavg": (177, 185), "tmax": (187, 195), "ice_depth": (197, 208)}


def fetch() -> Path:
    for name, rel in FILES.items():
        download(BASE + rel, RAW / name)
    return RAW / "dlre_prp_south.tab"


def read_prp(path: Path, min_lat: float = -80.0) -> pd.DataFrame:
    df = pd.read_fwf(path, colspecs=list(COLSPECS.values()), names=list(COLSPECS), skiprows=1, dtype=float)
    df = df[df["lat"] <= min_lat].copy()
    df["lon"] = (df["lon"] + 180.0) % 360.0 - 180.0
    for c in ("tavg", "tmax"):
        df.loc[(df[c] <= 0) | (df[c] > 500), c] = np.nan  # fill values
    df.loc[df["ice_depth"] < 0, "ice_depth"] = np.nan
    return df


def build_thermal() -> list[Path]:
    df = read_prp(fetch())
    x, y = geo.latlon_to_xy(df["lat"].to_numpy(), df["lon"].to_numpy(), engine.COARSE_DEM)
    half = 304000.0
    n = int(2 * half / CELL_M)
    col = np.floor((x + half) / CELL_M).astype(int)
    row = np.floor((half - y) / CELL_M).astype(int)
    ok = (col >= 0) & (col < n) & (row >= 0) & (row < n)
    idx = row[ok] * n + col[ok]
    out = {}
    for c in ("tavg", "tmax", "ice_depth"):
        v = df[c].to_numpy()[ok]
        good = np.isfinite(v)
        s = np.bincount(idx[good], weights=v[good], minlength=n * n)
        k = np.bincount(idx[good], minlength=n * n)
        with np.errstate(invalid="ignore"):
            out[c] = np.where(k > 0, s / np.maximum(k, 1), np.nan).reshape(n, n).astype(np.float32)
    centres = -half + CELL_M * (np.arange(n) + 0.5)
    np.savez_compressed(GRID_NPZ, x=centres, y=centres[::-1], cell_m=CELL_M, cold_trap_k=COLD_TRAP_K, **out)

    tree = cKDTree(np.c_[x, y])
    rows = []
    for s in load_sites():
        if not s["in_polar_dem"]:
            continue
        sx, sy = geo.latlon_to_xy(s["lat"], s["lon"], engine.COARSE_DEM)
        near = tree.query_ball_point([sx, sy], SITE_RADIUS_M)
        sub = df.iloc[near]
        rows.append({"site_id": s["id"], "n_triangles": len(sub), "tmax_k": sub["tmax"].mean(), "tavg_k": sub["tavg"].mean(),
                     "tmax_min_k": sub["tmax"].min(), "ice_depth_m": sub["ice_depth"].median(),
                     "cold_trap_share": float((sub["tmax"] < COLD_TRAP_K).mean()) if len(sub) else np.nan})
    pd.DataFrame(rows).to_csv(SITE_CSV, index=False, float_format="%.2f")
    return [GRID_NPZ, SITE_CSV]


if __name__ == "__main__":
    for p in build_thermal():
        print(p, f"{p.stat().st_size / 1e6:.2f} MB")
