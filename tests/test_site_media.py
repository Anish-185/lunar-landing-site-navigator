"""Design v2 inputs: the packed polar heightmap the story site relights, and the real Sun/Earth directions."""

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling

from pipeline import export_site, media

ROOT = Path(__file__).resolve().parents[1]
DEM = ROOT / "data" / "derived" / "dem_80s_160m.tif"


def test_heightmap_round_trips_to_the_dem_within_quantisation():
    rgb, meta = media.heightmap(DEM, width=256)
    q = rgb[0].astype(np.uint32) * 256 + rgb[1]
    z = meta["min_m"] + q / 65535 * (meta["max_m"] - meta["min_m"])
    with rasterio.open(DEM) as ds:
        ref = ds.read(1, out_shape=(rgb.shape[1], 256), resampling=Resampling.average, masked=True).astype(float).filled(np.nan)
    ok = (rgb[2] == 255) & np.isfinite(ref)
    assert ok.mean() > 0.5
    assert np.nanmax(np.abs(z[ok] - ref[ok])) < 4.0          # 16-step low byte: ~3.5 m, plus rounding of the range
    assert meta["px_m"] > 0 and meta["width"] == 256


def test_committed_heightmap_matches_its_metadata():
    meta = json.loads((ROOT / "site" / "public" / "media" / "pole_height.json").read_text())
    with rasterio.open(ROOT / "site" / "public" / "media" / "pole_height.png") as ds:
        assert ds.count == 3 and ds.width == meta["width"]


def test_light_vectors_are_unit_and_the_sun_is_near_the_lunar_equator_plane():
    d = export_site.light()
    for body in ("sun", "earth"):
        assert abs(np.linalg.norm(d[body]) - 1) < 1e-3
    assert abs(d["sun"][2]) < 0.03            # the Moon's axis is tilted only ~1.5° to the ecliptic
    assert d["earth"][0] > 0.95               # the near side faces Earth: sub-Earth point near lon 0
