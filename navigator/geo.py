"""Geometry and raster helpers.

- latlon_to_xy / xy_to_latlon: lat/lon (degrees) <-> projected x/y (metres) in the CRS read from a data file.
- read_window: a square DEM window around a site, read with rasterio (remote files via GDAL /vsicurl/ range reads).
- gdal_compat / osr_compat: the few GDAL and OSR calls that the vendored NASA MMGIS HorizonProfile.py makes,
  on top of rasterio and pyproj, so it runs in the deployed app without the GDAL Python bindings.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pyproj
import rasterio
from rasterio.windows import Window

# Keeps /vsicurl/ from listing the remote directory and probing for sidecar files on open.
VSICURL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF"}


def _gdal_path(src: str | Path) -> str:
    src = str(src)
    return f"/vsicurl/{src}" if src.startswith(("http://", "https://")) else src


def _is_file(s: str) -> bool:
    """True for an existing path; False for anything else, including WKT strings longer than a path may be."""
    if "[" in s or len(s) > 1024:
        return False
    try:
        return Path(s).exists()
    except OSError:
        return False


def _crs(crs_or_path) -> pyproj.CRS:
    s = str(crs_or_path)
    if isinstance(crs_or_path, (str, Path)) and (s.startswith(("http://", "https://")) or _is_file(s)):
        with rasterio.Env(**VSICURL_ENV), rasterio.open(_gdal_path(s)) as ds:
            return pyproj.CRS.from_wkt(ds.crs.to_wkt())
    return pyproj.CRS.from_user_input(crs_or_path)


@lru_cache(maxsize=16)
def _transformers(wkt: str) -> tuple[pyproj.Transformer, pyproj.Transformer]:
    crs = pyproj.CRS.from_wkt(wkt)
    fwd = pyproj.Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    return fwd, pyproj.Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)


def latlon_to_xy(lat, lon, crs):
    """Projected (x, y) in metres. `crs`: a raster path/URL, WKT, or anything pyproj accepts."""
    return _transformers(_crs(crs).to_wkt())[0].transform(lon, lat)


def xy_to_latlon(x, y, crs):
    """(lat, lon) in degrees, lon east-positive in [-180, 180)."""
    lon, lat = _transformers(_crs(crs).to_wkt())[1].transform(x, y)
    return lat, (np.asarray(lon) + 180.0) % 360.0 - 180.0


def read_window(src, lat: float, lon: float, half_size_m: float, out_path: str | Path | None = None):
    """Square window of band 1 centred on (lat, lon), clipped to the raster.

    `src` is a local path or an http(s) URL (read remotely with /vsicurl/ range requests).
    Returns (array, profile); `profile` is a rasterio profile for the window (transform, size, CRS, nodata).
    With `out_path`, the window is also written there as a GeoTIFF.
    """
    with rasterio.Env(**VSICURL_ENV), rasterio.open(_gdal_path(src)) as ds:
        x, y = latlon_to_xy(lat, lon, ds.crs.to_wkt())
        row, col = ds.index(x, y)
        half_px = int(np.ceil(half_size_m / abs(ds.res[0])))
        win = Window(col - half_px, row - half_px, 2 * half_px + 1, 2 * half_px + 1)
        win = win.intersection(Window(0, 0, ds.width, ds.height))
        data = ds.read(1, window=win)
        profile = ds.profile | {"driver": "GTiff", "width": win.width, "height": win.height,
                                "transform": ds.window_transform(win), "tiled": False}
        for key in ("blockxsize", "blockysize", "compress", "interleave"):
            profile.pop(key, None)
    if out_path is not None:
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(data, 1)
    return data, profile


# --- GDAL/OSR stand-ins for the vendored MMGIS HorizonProfile.py (only the calls it makes) ---

class _Band:
    def __init__(self, ds):
        self._ds = ds

    def ReadAsArray(self, xoff=0, yoff=0, win_xsize=None, win_ysize=None):
        w = Window(xoff, yoff, win_xsize or self._ds.width, win_ysize or self._ds.height)
        return self._ds.read(1, window=w)

    def GetNoDataValue(self):
        return self._ds.nodata


class _Dataset:
    def __init__(self, path, *_):
        with rasterio.Env(**VSICURL_ENV):
            self._ds = rasterio.open(_gdal_path(path))
        self.RasterXSize, self.RasterYSize = self._ds.width, self._ds.height

    def GetGeoTransform(self):
        return self._ds.transform.to_gdal()

    def GetProjection(self):
        return self._ds.crs.to_wkt()

    def GetRasterBand(self, _index=1):
        return _Band(self._ds)


class _SpatialReference:
    def __init__(self, crs: pyproj.CRS | None = None):
        self.crs = crs

    def SetAxisMappingStrategy(self, _strategy):  # always lon/lat (x/y) order below
        pass

    def ImportFromWkt(self, wkt):
        self.crs = pyproj.CRS.from_wkt(wkt)

    def IsProjected(self):
        return int(self.crs.is_projected)

    def GetLinearUnits(self):
        return self.crs.axis_info[0].unit_conversion_factor

    def GetAttrValue(self, key, _child=0):
        m = re.search(rf'{key}\["([^"]+)"', self.crs.to_wkt("WKT1_GDAL"))
        return m.group(1) if m else None

    def GetProjParm(self, name, default=0.0):
        m = re.search(rf'PARAMETER\["{name}",([-0-9.eE+]+)\]', self.crs.to_wkt("WKT1_GDAL"))
        return float(m.group(1)) if m else default

    def CloneGeogCS(self):
        return _SpatialReference(self.crs.geodetic_crs)


class _CoordinateTransformation:
    def __init__(self, src: _SpatialReference, dst: _SpatialReference):
        self._t = pyproj.Transformer.from_crs(src.crs, dst.crs, always_xy=True)

    def TransformPoint(self, x, y, z=0.0):
        return (*self._t.transform(x, y), z)


gdal_compat = SimpleNamespace(Open=_Dataset, UseExceptions=lambda: None, GA_ReadOnly=0)
osr_compat = SimpleNamespace(SpatialReference=_SpatialReference, CoordinateTransformation=_CoordinateTransformation,
                             OAMS_TRADITIONAL_GIS_ORDER=0)
GDAL_COMPAT_VERSION = "3.compat"  # HorizonProfile.py only checks the major version


# --- naming the terrain that blocks the Sun or Earth ("blame the ridge") ---

MOON_RADIUS_M = 1737400.0
LOCAL_SLOPE_M = 500.0  # occluders closer than this are "the local slope"


def great_circle_m(lat1, lon1, lat2, lon2):
    """Distance on the 1737.4 km sphere (haversine), broadcasting over arrays."""
    p1, p2, dl = np.radians(lat1), np.radians(lat2), np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * MOON_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def name_points(lat, lon, features) -> tuple[np.ndarray, np.ndarray]:
    """For each point, the named feature it belongs to and how ("rim", "inside", "on", "near"), or "" if none.

    `features`: table with name, lat, lon, diameter_km, kind ("crater" | "mons"), e.g. data/derived/lunar_features.csv.
    A feature's footprint is a circle of its diameter. Among features whose footprint contains the point, the
    smallest wins (most specific); otherwise, among features within 1.5 radii, the one whose rim is closest (km).
    """
    lat, lon = np.atleast_1d(lat).astype(float), np.atleast_1d(lon).astype(float)
    flat, flon = np.asarray(features["lat"], float), np.asarray(features["lon"], float)
    radius = np.asarray(features["diameter_km"], float) * 500.0
    # Pre-filter (same result, much faster): drop features whose 1.5-radius circle cannot reach the points' latitudes.
    reach = np.degrees(1.5 * radius / MOON_RADIUS_M)
    if np.isfinite(lat).any():
        keep = (flat - reach <= np.nanmax(lat)) & (flat + reach >= np.nanmin(lat))
        if not keep.any():
            empty = np.full(len(lat), "", dtype=object).astype(str)
            return empty, empty
        features = {k: np.asarray(features[k])[keep] for k in ("name", "kind")}
        flat, flon, radius = flat[keep], flon[keep], radius[keep]
    d = great_circle_m(lat[:, None], lon[:, None], flat[None, :], flon[None, :]) / radius[None, :]
    big = np.broadcast_to(radius, d.shape)
    inside_pick = np.where(d <= 1.0, big, np.inf).argmin(axis=1)
    near_pick = np.where(d <= 1.5, (d - 1.0) * big, np.inf).argmin(axis=1)  # closest rim, in metres
    has_inside = (d <= 1.0).any(axis=1)
    pick = np.where(has_inside, inside_pick, near_pick)
    ratio = d[np.arange(len(lat)), pick]
    found = ratio <= 1.5
    kinds = np.asarray(features["kind"])[pick]
    relation = np.where(kinds == "mons", np.where(ratio <= 1.0, "on", "near"),
                        np.where(ratio < 0.8, "inside", np.where(ratio <= 1.2, "rim", "near")))
    names = np.where(found & np.isfinite(lat), np.asarray(features["name"])[pick], "")
    return names.astype(str), np.where(names != "", relation, "").astype(str)


def blame_line(body: str, name: str, relation: str, distance_m: float, azimuth_deg: float) -> str:
    """'Sun blocked by the rim of Shackleton, 21 km away at az 212°' (plain English for the UI).
    Occluders closer than LOCAL_SLOPE_M are the ground around the site itself, not a distant ridge."""
    where = {"rim": f"the rim of {name}", "inside": f"terrain inside {name}", "on": name,
             "near": f"terrain near {name}"}.get(relation, "unnamed terrain")
    if distance_m < LOCAL_SLOPE_M:
        where = "the local slope"
    km = distance_m / 1000.0
    dist = f"{km:.0f} km" if km >= 2 else f"{distance_m:.0f} m"
    return f"{body} blocked by {where}, {dist} away at az {azimuth_deg:.0f}°"
