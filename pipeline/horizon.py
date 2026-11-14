"""Phase 3. Terrain horizons from the vendored NASA MMGIS Sightline scripts:
site horizons with occluder per azimuth -> data/derived/horizons/<site_id>.npz,
landing-ellipse sample points -> data/derived/tiles/<site_id>.npz, and shadow snapshots.

Phase 1 part: build_coarse_dem, the shipped DEM that custom sites use at runtime.
"""

from __future__ import annotations

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
