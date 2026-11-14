"""navigator.geo: projections read from the data files, DEM windows, and the GDAL/OSR stand-ins."""

import math
from pathlib import Path

import numpy as np
import pytest
import rasterio

from navigator import geo

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
DEM80 = RAW / "pgda90" / "LDEM_80S_80MPP_ADJ.TIF"
SMALL = [RAW / "pgda69" / "AVGVISIB_85S_060M_201608_COG.TIF", RAW / "pgda69" / "AVGVISIB_75S_120M_201608_COG.TIF", DEM80]
R_MOON = 1737400.0


def _need(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"{path.name} not downloaded (make data)")
    return path


@pytest.fixture(scope="module")
def raster():
    """Any downloaded south-polar raster; the projection always comes from the file."""
    for p in SMALL:
        if p.exists():
            return p
    pytest.skip("no south-polar raster downloaded (make data)")


def test_file_crs_is_polar_stereographic_on_lunar_sphere(raster):
    crs = geo._crs(raster).to_dict()
    assert crs["proj"] == "stere" and crs["lat_0"] == -90 and crs["R"] == R_MOON


def test_pole_maps_to_origin(raster):
    x, y = geo.latlon_to_xy(-90.0, 0.0, raster)
    assert abs(x) < 1e-6 and abs(y) < 1e-6


@pytest.mark.parametrize("lon, sx, sy", [(0, 0, 1), (90, 1, 0), (180, 0, -1), (-90, -1, 0)])
def test_stereographic_radius_and_direction(raster, lon, sx, sy):
    # South polar stereographic, true scale at the pole: rho = 2R tan(colat/2), x = rho sin(lon), y = rho cos(lon).
    rho = 2 * R_MOON * math.tan(math.radians(5.0) / 2)
    x, y = geo.latlon_to_xy(-85.0, lon, raster)
    assert x == pytest.approx(sx * rho, abs=1e-3) and y == pytest.approx(sy * rho, abs=1e-3)


def test_round_trip_is_exact_and_lon_wrapped(raster):
    rng = np.random.default_rng(0)
    lat, lon = rng.uniform(-89.99, -80, 1000), rng.uniform(-180, 180, 1000)
    x, y = geo.latlon_to_xy(lat, lon, raster)
    lat2, lon2 = geo.xy_to_latlon(x, y, raster)
    assert np.max(np.abs(lat2 - lat)) < 1e-9
    assert np.max(np.abs((lon2 - lon + 180) % 360 - 180)) < 1e-7
    assert lon2.min() >= -180 and lon2.max() < 180


def test_read_window_centre_size_and_geotiff(tmp_path):
    dem = _need(DEM80)
    lat, lon, half = -89.45, -137.3, 2000.0
    data, profile = geo.read_window(dem, lat, lon, half, out_path=tmp_path / "w.tif")
    n = 2 * math.ceil(half / 80) + 1
    assert data.shape == (n, n)
    x, y = geo.latlon_to_xy(lat, lon, dem)
    with rasterio.open(dem) as ds:
        expected = next(ds.sample([(x, y)]))[0]
    assert data[n // 2, n // 2] == expected
    with rasterio.open(tmp_path / "w.tif") as w:
        np.testing.assert_array_equal(w.read(1), data)
        assert w.crs == rasterio.crs.CRS.from_user_input(profile["crs"])
        assert next(w.sample([(x, y)]))[0] == expected


def test_read_window_is_clipped_at_raster_edge():
    dem = _need(DEM80)
    data, _ = geo.read_window(dem, -80.05, 0.0, 20000.0)  # window runs past the 80S edge
    full = 2 * math.ceil(20000 / 80) + 1
    assert data.shape[1] == full and data.shape[0] < full


@pytest.mark.network
def test_remote_20m_window_matches_local_80m():
    from pipeline.fetch_data import REMOTE_20M

    dem = _need(DEM80)
    remote, _ = geo.read_window(REMOTE_20M["ldem_20m"], -85.0, 30.0, 2000.0)
    local, _ = geo.read_window(dem, -85.0, 30.0, 2000.0)
    assert remote.shape == (201, 201)
    assert abs(np.nanmean(remote) - np.nanmean(local)) < 30.0  # same terrain, different resolution


# --- the GDAL/OSR stand-ins must answer every call HorizonProfile.py makes exactly as GDAL does ---

@pytest.fixture(scope="module")
def both(raster):
    osgeo = pytest.importorskip("osgeo")
    from osgeo import gdal, osr

    gdal.UseExceptions()
    return (gdal.Open(str(raster)), osr), (geo.gdal_compat.Open(str(raster)), geo.osr_compat)


def test_dataset_and_band_match_gdal(both):
    (ds, _), (cds, _) = both
    assert cds.RasterXSize == ds.RasterXSize and cds.RasterYSize == ds.RasterYSize
    assert cds.GetGeoTransform() == pytest.approx(ds.GetGeoTransform())
    b, cb = ds.GetRasterBand(1), cds.GetRasterBand(1)
    nd, cnd = b.GetNoDataValue(), cb.GetNoDataValue()
    assert (nd is None and cnd is None) or nd == cnd or (math.isnan(nd) and math.isnan(cnd))
    args = (ds.RasterXSize // 2 - 50, ds.RasterYSize // 2 - 70, 100, 140)
    np.testing.assert_array_equal(cb.ReadAsArray(*args), b.ReadAsArray(*args))


def test_spatial_reference_matches_osr(both):
    (ds, osr), (cds, cosr) = both
    s, cs = osr.SpatialReference(), cosr.SpatialReference()
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    cs.SetAxisMappingStrategy(cosr.OAMS_TRADITIONAL_GIS_ORDER)
    s.ImportFromWkt(ds.GetProjection())
    cs.ImportFromWkt(cds.GetProjection())
    assert bool(cs.IsProjected()) == bool(s.IsProjected())
    assert cs.GetLinearUnits() == s.GetLinearUnits()
    assert cs.GetAttrValue("PROJECTION", 0).lower() == s.GetAttrValue("PROJECTION", 0).lower()
    for name in ("false_easting", "false_northing", "latitude_of_origin"):
        assert cs.GetProjParm(name, 0.0) == pytest.approx(s.GetProjParm(name, 0.0))
    ct = osr.CoordinateTransformation(s.CloneGeogCS(), s)
    cct = cosr.CoordinateTransformation(cs.CloneGeogCS(), cs)
    for lon, lat in [(0, -85), (90, -88), (-137.3, -89.45), (179.9, -80.5)]:
        assert cct.TransformPoint(lon, lat)[:2] == pytest.approx(ct.TransformPoint(lon, lat)[:2], abs=1e-6)
