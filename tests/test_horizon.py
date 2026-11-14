"""Terrain horizons: the vendored MMGIS ray march on synthetic DEMs (both GDAL and our rasterio/pyproj stand-ins),
occluder bookkeeping on real output, naming, PSR distances."""

import math

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from navigator import geo
from pipeline import horizon as H
from vendor.mmgis_sightline import HorizonProfile as hp

R = 1737400.0
CRS = "+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"


@pytest.fixture(params=["gdal", "compat"])
def backend(request, monkeypatch):
    if request.param == "compat":
        monkeypatch.setattr(hp, "gdal", geo.gdal_compat)
        monkeypatch.setattr(hp, "osr", geo.osr_compat)
        monkeypatch.setattr(hp, "osgeoversion", geo.GDAL_COMPAT_VERSION)
    elif hp.gdal is geo.gdal_compat:
        pytest.skip("GDAL bindings not installed")
    return request.param


def _dem(tmp_path, lat, lon, half_px, px_m, fill=0.0):
    """Flat synthetic DEM (heights above the sphere) centred on (lat, lon); returns path, array, observer row/col."""
    x0, y0 = geo.latlon_to_xy(lat, lon, CRS)
    n = 2 * half_px + 1
    z = np.full((n, n), fill, np.float32)
    path = tmp_path / "dem.tif"
    transform = from_origin(x0 - (half_px + 0.5) * px_m, y0 + (half_px + 0.5) * px_m, px_m, px_m)

    def write():
        with rasterio.open(path, "w", driver="GTiff", width=n, height=n, count=1, dtype="float32", crs=CRS,
                           transform=transform) as ds:
            ds.write(z, 1)
        return path
    return write, z, half_px


def test_smooth_sphere_gives_geometric_dip(tmp_path, backend):
    write, z, c = _dem(tmp_path, -85.0, 0.0, 600, 50.0)
    h = 100.0
    prof = hp.compute_horizon_profile(write(), -85.0, 0.0, h, 72, 29000.0, 0.0, R)
    expected = -math.degrees(math.acos(R / (R + h)))  # -0.615 deg, horizon 18.6 km away
    assert np.max(np.abs(prof[:, 1] - expected)) < 0.02
    assert np.all(np.abs(prof[:, 2] - math.sqrt(2 * R * h)) < 2500)


def test_wall_gives_atan_h_over_d_minus_curvature(tmp_path, backend):
    write, z, c = _dem(tmp_path, -85.0, 0.0, 400, 20.0)
    wall_h, eye = 300.0, 2.0
    z[c - 120: c - 100, :] = wall_h  # grid north of the observer (= local north on the 0 deg meridian), 2.0-2.4 km away
    prof = hp.compute_horizon_profile(write(), -85.0, 0.0, eye, 720, 7000.0, 0.0, R)
    el, d = prof[0, 1], prof[0, 2]  # azimuth 0
    assert 2000 - 20 <= d <= 2400
    assert el == pytest.approx(math.degrees(math.atan((wall_h - d * d / (2 * R) - eye) / d)), abs=0.011)
    assert el > 7.0  # really the wall, not the flat ground


def test_ridge_grid_north_at_lon_90e_is_due_west(tmp_path, backend):
    # At 90 E on a south polar stereographic grid, local north is +x and grid north (+y) points due west (az 270).
    write, z, c = _dem(tmp_path, -85.0, 90.0, 300, 20.0)
    z[c - 160: c - 140, c - 5: c + 6] = 500.0  # a short ridge 3 km grid-north of the observer
    prof = hp.compute_horizon_profile(write(), -85.0, 90.0, 2.0, 720, 5500.0, 0.0, R)
    blocked = prof[prof[:, 1] > 5.0, 0]  # the ridge spans ~+/-2 deg of azimuth; check the centre of that arc
    assert 0 < len(blocked) < 40 and abs(blocked.mean() - 270.0) <= 0.5


def test_occluder_lies_on_the_dem_at_the_reported_distance():
    if not (H.HORIZON_DIR / "im2_actual.npz").exists() or not H.DEM80.exists():
        pytest.skip("run make data && make derived")
    hz = H.load_horizon("im2_actual")
    site_x, site_y = geo.latlon_to_xy(float(hz["site_lat"]), float(hz["site_lon"]), H.COARSE_DEM)
    k = list(hz["masts"]).index(2.0)
    near = H.window_path("im2_actual", "ldem_20m")
    eye = H._sample(near, site_x, site_y)[0] + 2.0
    for i in range(0, 720, 15):
        x, y, d, el = hz["x"][k, i], hz["y"][k, i], hz["dist"][k, i], hz["el"][k, i]
        assert math.hypot(x - site_x, y - site_y) == pytest.approx(d, abs=120)  # within ~1.5 px
        lat, lon = hz["lat"][k, i], hz["lon"][k, i]
        assert np.allclose(geo.latlon_to_xy(lat, lon, H.COARSE_DEM), (x, y), atol=0.5)
        dem = near if hz["field"][k, i] == 0 else H.DEM80
        zt = H._sample(dem, x, y)[0]
        assert el == pytest.approx(math.degrees(math.atan2(zt - d * d / (2 * R) - eye, d)), abs=0.05)


def test_name_points_prefers_smallest_containing_feature_and_rims():
    feats = pd.DataFrame({"name": ["Big", "Small", "Peak"], "lat": [-85.0, -85.0, -86.0], "lon": [0.0, 1.0, 50.0],
                          "diameter_km": [200.0, 20.0, 10.0], "kind": ["crater", "crater", "mons"]})
    small_x, small_y = geo.latlon_to_xy(-85.0, 1.0, CRS)
    rim_lat, rim_lon = geo.xy_to_latlon(small_x + 10000.0, small_y, CRS)  # 10 km = Small's radius
    names, rel = geo.name_points([rim_lat, -85.0, -86.0, -60.0], [rim_lon, 1.0, 50.0, 0.0], feats)
    assert list(names) == ["Small", "Small", "Peak", ""]
    assert list(rel) == ["rim", "inside", "on", ""]
    assert geo.blame_line("Sun", "Shackleton", "rim", 21400, 212.3) == "Sun blocked by the rim of Shackleton, 21 km away at az 212°"
    assert geo.blame_line("Earth", "", "", 72, 332) == "Earth blocked by the local slope, 72 m away at az 332°"


def test_outside_every_circle_the_closest_rim_wins_not_the_biggest_crater():
    # Point at 85 S 0 E. Mid: centre 30 km away, radius 25 km (d/R 1.21, rim 5 km away).
    # Huge: centre 230 km away, radius 200 km (d/R 1.15, rim 30 km away). Old rule (d/R) picked Huge.
    feats = pd.DataFrame({"name": ["Huge", "Mid"], "lat": [-77.41, -86.0], "lon": [0.0, 0.0],
                          "diameter_km": [400.0, 50.0], "kind": ["crater", "crater"]})
    names, rel = geo.name_points([-85.0], [0.0], feats)
    assert names[0] == "Mid" and rel[0] == "near"


def test_psr_distance_is_zero_inside_and_positive_outside():
    if not H.PSR_SHP.exists():
        pytest.skip("PSR shapefile not downloaded (make data)")
    psr = H._psr()
    inside = psr.geometry.iloc[0].representative_point()
    d = H.psr_distances([inside.x, inside.x + 50000.0], [inside.y, inside.y + 50000.0])
    assert d["dist_m"].iloc[0] == 0 and d["dist_m"].iloc[1] > 0


def test_derived_horizons_cover_every_site():
    from pipeline.sites import load_sites

    for s in load_sites():
        hz = H.load_horizon(s["id"])
        assert hz["el"].shape == (len(H.MASTS), H.N_AZ)
        assert str(hz["horizon_source"]) == ("ldem_80s_20m+80m" if s["in_polar_dem"] else
                                             str(hz["horizon_source"]))
        if not s["in_polar_dem"] and s["id"] != "chandrayaan_3":
            assert str(hz["horizon_source"]) == "smooth_sphere"
        assert np.all(np.diff(hz["el"].mean(axis=1)) <= 1e-6)  # a taller mast never raises the horizon


def test_psr_outlines_small_enough_for_the_app():
    assert H.PSR_GEOJSON.stat().st_size < 5_000_000


def test_tiles_have_200_points_spread_by_the_lander_sigma():
    from pipeline.sites import load_landers, load_sites

    landers = load_landers()
    for s in load_sites():
        if not s["in_polar_dem"]:
            continue
        with np.load(H.TILE_DIR / f"{s['id']}.npz") as t:
            assert t["h_el"].shape == (H.ELLIPSE_N, H.N_AZ)
            assert str(t["lander"]) == s["lander"] and float(t["sigma_m"]) == landers[s["lander"]]["ellipse_sigma_m"]
            x0, y0 = geo.latlon_to_xy(s["lat"], s["lon"], H.COARSE_DEM)
            spread = np.std(np.hypot(t["x"] - x0, t["y"] - y0)) / float(t["sigma_m"])
            assert 0.4 < spread < 1.0  # Rayleigh: std of radius = 0.655 sigma
            assert np.all(np.isfinite(t["slope_deg"])) and np.all(t["psr_dist_m"] >= 0)
            assert not any('"' in n for n in t["psr_name"])


def test_avgvisib_validation_is_saved_and_mostly_close():
    df = pd.read_csv(H.AVGVISIB_CSV)
    assert len(df) == 14
    close = (df["diff_sun"].abs() < 0.03).sum()
    assert close >= 11  # documented outliers: Peak near Cabeus B, Blue Moon MK1 ridge (docs/METHOD.md)


def test_shadow_snapshot_at_athena_touchdown():
    pytest.importorskip("numba")
    pytest.importorskip("osgeo")
    from pipeline.sites import site_by_id

    if not H.window_path("im2_actual", "ldem_20m").exists():
        pytest.skip("20 m window not cached (make derived)")
    s = site_by_id("im2_actual")
    snap = H.shadow_snapshot(s, s["landing_utc"])
    assert snap["grid"].shape == (30, 30) and set(np.unique(snap["grid"])) <= {0, 1, 9}
    assert 2.0 < float(snap["el"]) < 3.0  # low Sun at touchdown
