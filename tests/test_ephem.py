"""Ephemeris: agreement with JPL Horizons, conventions, derived files, and physical sanity checks."""

import numpy as np
import pandas as pd
import pytest

from navigator import engine
from pipeline import ephem
from pipeline.sites import load_sites, site_by_id

TOLERANCE_DEG = 0.02


def _year(site_id, year=2027):
    d = pd.read_parquet(ephem.EPHEM_DIR / f"{site_id}.parquet")
    return d[d["utc"].dt.year == year]


# --- validation (offline: cached Horizons responses in tests/fixtures/horizons.csv) ---

def test_matches_jpl_horizons_within_tolerance():
    res = ephem.horizons_residuals()
    assert len(res) == 130  # 3 sites x 20 epochs x 2 bodies + Athena 5 epochs x 2 bodies
    worst = res.loc[res["sep"].idxmax()]
    assert res["sep"].max() < TOLERANCE_DEG, f"worst: {worst.to_dict()}"


def test_validation_csv_is_current():
    saved = pd.read_csv(ephem.VALIDATION_CSV)
    assert len(saved) == 130 and saved["sep"].max() < TOLERANCE_DEG


@pytest.mark.network
def test_refresh_horizons_fixtures():
    fresh = ephem.fetch_horizons_fixtures()  # overwrites tests/fixtures/horizons.csv
    assert len(fresh) == 130
    assert ephem.horizons_residuals()["sep"].max() < TOLERANCE_DEG


# --- conventions ---

def test_angular_radii():
    assert engine.sun_radius_deg(149_597_870.7) == pytest.approx(0.2666, abs=1e-4)
    assert engine.earth_radius_deg(384_400.0) == pytest.approx(0.9496, abs=1e-4)


def test_azimuth_is_compass_east_is_90():
    # Apollo 11 is ~23.5 deg east of the sub-Earth point, so Earth hangs in the western sky (az ~ 270).
    d = _year("apollo_11")
    assert abs(d["earth_az"].median() - 270) < 15


def test_azimuth_zero_is_local_north():
    # From 85 S on the 0 deg meridian, Earth (near the lunar equator, lon ~0) is due north: az ~ 0/360.
    d = engine.sun_earth_azel(-85.0, 0.0, pd.date_range("2027-01-01", periods=30, freq="D", tz="UTC"))
    assert np.all(np.minimum(d["earth_az"], 360 - d["earth_az"]) < 10)


def test_pipeline_files_match_engine_and_cover_every_window():
    n = len(ephem.hourly_utc())
    for site in load_sites():
        d = pd.read_parquet(ephem.EPHEM_DIR / f"{site['id']}.parquet")
        assert list(d.columns) == engine.COLUMNS and len(d) == n and str(d["utc"].dt.tz) == "UTC"
    s = site_by_id("im2_actual")
    d = pd.read_parquet(ephem.EPHEM_DIR / "im2_actual.parquet").iloc[[0, 5000, -1]].reset_index(drop=True)
    fresh = engine.sun_earth_azel(s["lat"], s["lon"], d["utc"])
    for col in engine.COLUMNS[1:]:
        np.testing.assert_allclose(d[col], fresh[col], rtol=1e-6, atol=1e-4)


# --- physical sanity checks (no terrain yet) ---

@pytest.mark.parametrize("site_id", ["change_7_target", "blue_moon_mk1_target"])
def test_polar_sun_skims_horizon(site_id):
    # Sun elevation is bounded by colatitude + the Moon's 1.54 deg axial tilt: about +/-2 deg near the pole.
    colat = 90 - abs(site_by_id(site_id)["lat"])
    sun = _year(site_id)["sun_el"]
    assert sun.abs().max() < colat + 1.6
    assert sun.max() > colat + 1.3 and sun.min() < -(colat + 1.3)  # a full year reaches both extremes


def test_shackleton_rim_earth_bobs_and_is_up_about_half_the_time():
    earth = _year("change_7_target")["earth_el"]
    assert earth.abs().max() < 8.5 and earth.max() > 4 and earth.min() < -4  # libration in latitude ~ +/-6.7 deg
    assert 0.35 < (earth > 0).mean() < 0.65


def test_apollo_11_earth_stays_high_all_month():
    d = _year("apollo_11")
    for month in range(1, 13):
        assert d[d["utc"].dt.month == month]["earth_el"].min() > 50
