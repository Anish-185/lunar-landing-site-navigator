"""data/derived/dem_80s_160m.tif: the shipped DEM for custom sites (committed, so these always run)."""

import numpy as np
import pytest
import rasterio

from pipeline.horizon import COARSE_DEM, DEM80, INT16_NODATA


@pytest.fixture(scope="module")
def coarse():
    assert COARSE_DEM.exists(), "run `make derived`"
    with rasterio.open(COARSE_DEM) as ds:
        yield ds


def test_format(coarse):
    assert coarse.dtypes[0] == "int16" and coarse.nodata == INT16_NODATA
    assert coarse.res == (160.0, 160.0)
    assert coarse.block_shapes[0] == (512, 512) and coarse.compression.name.lower() == "deflate"
    assert COARSE_DEM.stat().st_size < 50e6


def test_matches_2x2_block_average_of_source(coarse):
    if not DEM80.exists():
        pytest.skip("LDEM_80S_80MPP_ADJ.TIF not downloaded (make data)")
    with rasterio.open(DEM80) as src:
        assert src.crs == coarse.crs and src.bounds == pytest.approx(coarse.bounds)
        fine = src.read(1, window=rasterio.windows.Window(2000, 3000, 400, 400)).astype(np.float64)
    block = fine.reshape(200, 2, 200, 2).mean(axis=(1, 3))
    got = coarse.read(1, window=rasterio.windows.Window(1000, 1500, 200, 200)).astype(np.float64)
    assert np.max(np.abs(got - block)) <= 0.5 + 1e-6  # rounding to whole metres only
