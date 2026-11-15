"""Smoke checks of every committed output in data/derived/ (what the app and story site read)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio

from pipeline.sites import load_sites

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data" / "derived"
SITES = load_sites()
POLAR = [s["id"] for s in SITES if s["in_polar_dem"]]


@pytest.mark.parametrize("site_id", [s["id"] for s in SITES])
def test_ephemeris_and_horizon_per_site(site_id):
    eph = pd.read_parquet(D / "ephem" / f"{site_id}.parquet")
    assert list(eph.columns) == ["utc", "sun_az", "sun_el", "sun_range_km", "earth_az", "earth_el", "earth_range_km"]
    assert eph["utc"].dt.tz is not None and len(eph) > 20000
    assert eph[["sun_az", "earth_az"]].stack().between(0, 360).all()
    with np.load(D / "horizons" / f"{site_id}.npz") as z:
        assert z["el"].shape == (6, 720) and np.isfinite(z["el"]).all()
        assert np.all(np.diff(z["el"], axis=0) <= 1e-3)  # higher mast never raises the horizon


@pytest.mark.parametrize("site_id", POLAR)
def test_tiles(site_id):
    with np.load(D / "tiles" / f"{site_id}.npz") as z:
        assert z["h_el"].shape == (200, 720)
        assert np.isfinite(z["slope_deg"]).all() and (z["slope_deg"] < 90).all()
        assert (z["psr_dist_m"] >= 0).all()


def test_tables():
    av = pd.read_csv(D / "validation_avgvisib.csv")
    rng = pd.read_csv(D / "validation_avgvisib_range.csv")
    assert set(av["site_id"]) == set(POLAR) == set(rng["site_id"])
    assert (rng["nasa_sun_min"] <= rng["nasa_sun"] + 1e-6).all() and (rng["nasa_sun"] <= rng["nasa_sun_max"] + 1e-6).all()
    hz = pd.read_csv(D / "validation_horizons.csv")
    assert hz["sep"].max() < 0.02
    assert len(pd.read_csv(D / "site_psr.csv")) == len(SITES)
    assert len(pd.read_csv(D / "lunar_features.csv")) > 1000


def test_coarse_dem_and_psr_outlines():
    with rasterio.open(D / "dem_80s_160m.tif") as ds:
        assert ds.crs is not None and abs(ds.transform.a) == 160
    import json
    gj = json.loads((D / "psr_outlines.geojson").read_text())
    assert len(gj["features"]) > 100
