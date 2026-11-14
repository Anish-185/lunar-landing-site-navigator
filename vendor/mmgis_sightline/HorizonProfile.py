# Vendored from NASA-AMMOS MMGIS, HorizonProfile.py
#   https://github.com/NASA-AMMOS/MMGIS/tree/c54c70f9f29af8f55fc67b0c424882047ef6af3d/plugins/core/backend/Sightline/scripts/HorizonProfile.py
#   Copyright 2020 California Institute of Technology. Apache License 2.0 (see LICENSE and NOTICE here).
# Changes by the Lunar Landing Site Navigator team (each marked [Lunar Navigator] in the code):
#   1. Guarded import: without osgeo, use navigator.geo.gdal_compat / osr_compat (rasterio + pyproj).
#   2. computeHorizonProfile also records the pixel (column, row) of the highest point on each ray.
#   3. Importable wrapper compute_horizon_profile(), which also returns that point's x/y and lat/lon.
#   4. (no SPICE in this file, so no frame/aberration change)
#   Everything else (ray march, curvature correction, grid convergence) is unchanged.

# HorizonProfile.py
#
# ============================================================================
# ALGORITHM DOCUMENTATION
# ============================================================================
#
# Overview
# --------
# Computes a 360° horizon silhouette (elevation profile) as seen from a single
# observer location on a DEM.  The result is an array of
# [azimuth_deg, max_horizon_elevation_deg] pairs — one per azimuth ray.
#
# Method: Radial Ray-March with Maximum Elevation Angle Tracking
# ---------------------------------------------------------------
# For each of N azimuth directions (0° .. 360°, step = 360/N):
#   1. March outward from the observer along that azimuth, sampling the DEM
#      at regular pixel-scale intervals.
#   2. At each sample compute the elevation angle from the observer to the
#      terrain sample:
#        el_angle = atan2(terrain_elev - observer_elev, dist_m)
#   3. Track the running maximum elevation angle along the ray.
#   4. After the march completes (either reaching max_radius_m or leaving
#      the DEM bounds), record [azimuth, max_elevation_angle] as the horizon
#      value for that direction.
#
# Parameters
# ----------
# - min_skip_radius_m : Ignore terrain within this distance (meters) from the
#   observer.  Useful for excluding the immediate surroundings (e.g. a lander
#   or instrument platform).
# - max_radius_m : Stop marching beyond this distance (meters).  Controls the
#   analysis footprint and performance.
# - planet_radius : If > 0, apply curvature correction to terrain elevations.
# - num_azimuths : Number of azimuth directions to sample (default 360).
#
# Curvature Correction
# --------------------
# When planet_radius > 0, terrain elevation at distance d is adjusted:
#   terrain_elev -= d² / (2 * planet_radius)
# This accounts for the apparent drop of distant terrain on a spherical body.
#
# Output
# ------
# JSON: {"horizonProfile": [[azimuth_deg, max_horizon_elevation_deg, distance_m], ...]}
# distance_m is the distance from the observer to the horizon point (meters).
#
# Usage: python HorizonProfile.py <raster_path> <lat> <lng> <observer_height>
#        <num_azimuths> <max_radius_m>
# ============================================================================

import sys
import json
import math
import numpy as np
try:
    from osgeo import gdal, osr
    from osgeo.gdalconst import GA_ReadOnly
    from osgeo import __version__ as osgeoversion
except ImportError:  # [Lunar Navigator] no GDAL (deployed app): rasterio/pyproj stand-ins
    from navigator.geo import gdal_compat as gdal, osr_compat as osr
    from navigator.geo import GDAL_COMPAT_VERSION as osgeoversion
    GA_ReadOnly = 0

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

gdal.UseExceptions()

NODATA_VALUE = -1100101


def latLonToPixel(ds, lat, lng):
    transform = ds.GetGeoTransform()
    xOrigin = transform[0]
    yOrigin = transform[3]
    pixelWidth = transform[1]
    pixelHeight = transform[5]

    srs = osr.SpatialReference()
    if int(osgeoversion[0]) >= 3:
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    srs.ImportFromWkt(ds.GetProjection())

    srsLatLong = srs.CloneGeogCS()
    ct = osr.CoordinateTransformation(srsLatLong, srs)

    (projX, projY, _) = ct.TransformPoint(lng, lat)
    px = (projX - xOrigin) / pixelWidth
    py = (projY - yOrigin) / pixelHeight

    if math.isinf(px):
        px = 0
    if math.isinf(py):
        py = 0

    return int(px), int(py)


def getPixelScale(ds):
    """Return approximate meters per pixel (average of x and y)."""
    transform = ds.GetGeoTransform()
    pixelWidth = abs(transform[1])
    pixelHeight = abs(transform[5])

    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())

    if srs.IsProjected():
        linear_unit = srs.GetLinearUnits()
        return ((pixelWidth + pixelHeight) / 2.0) * linear_unit
    else:
        mid_lat = transform[3] + (ds.RasterYSize / 2.0) * transform[5]
        deg2m = 111320.0 * math.cos(math.radians(mid_lat))
        return ((pixelWidth + pixelHeight) / 2.0) * deg2m


def _grid_convergence(ds, obs_px, obs_py):
    """Grid convergence (radians) at observer position.

    Only applies to azimuthal projections (stereographic, gnomonic) where
    meridians converge at the pole. For cylindrical projections (Equidistant
    Cylindrical, Mercator, etc.), grid north = geographic north so returns 0.
    Returns 0 for geographic (unprojected) CRS.
    """
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())
    if not srs.IsProjected():
        return 0.0
    proj_name = (srs.GetAttrValue('PROJECTION', 0) or '').lower()
    is_azimuthal = ('stereo' in proj_name or 'azimuthal' in proj_name
                    or 'gnomonic' in proj_name)
    if not is_azimuthal:
        return 0.0
    gt = ds.GetGeoTransform()
    x = gt[0] + obs_px * gt[1] + obs_py * gt[2]
    y = gt[3] + obs_px * gt[4] + obs_py * gt[5]
    fe = srs.GetProjParm('false_easting', 0.0)
    fn = srs.GetProjParm('false_northing', 0.0)
    lat_origin = srs.GetProjParm('latitude_of_origin', 0.0)
    north_sign = -1.0 if lat_origin > 0 else 1.0
    return math.atan2(x - fe, north_sign * (y - fn))


def computeHorizonProfile(ds, band, obs_px, obs_py, observer_height,
                          num_azimuths, max_radius_m,
                          min_skip_radius_m=0, planet_radius=0):
    pixel_scale = getPixelScale(ds)
    max_radius_px = max_radius_m / pixel_scale if pixel_scale > 0 else 500

    # Per-axis physical scale (m/pixel) for correct march direction & distance.
    # Geographic CRS pixels are non-square: 1° lon < 1° lat at non-zero lat.
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())
    gt = ds.GetGeoTransform()
    if srs.IsProjected():
        lu = srs.GetLinearUnits()
        px_scale_x = abs(gt[1]) * lu
        px_scale_y = abs(gt[5]) * lu
    else:
        obs_lat = gt[3] + obs_py * gt[5]
        px_scale_x = abs(gt[1]) * 111320.0 * math.cos(math.radians(obs_lat))
        px_scale_y = abs(gt[5]) * 111320.0

    xSize = ds.RasterXSize
    ySize = ds.RasterYSize

    margin = int(math.ceil(max_radius_px)) + 1
    xoff = max(obs_px - margin, 0)
    yoff = max(obs_py - margin, 0)
    xend = min(obs_px + margin + 1, xSize)
    yend = min(obs_py + margin + 1, ySize)
    regionW = xend - xoff
    regionH = yend - yoff

    if regionW <= 0 or regionH <= 0:
        return [[i * (360.0 / num_azimuths), 0.0, 0.0] for i in range(num_azimuths)]

    region = band.ReadAsArray(xoff, yoff, regionW, regionH)
    if region is None:
        return [[i * (360.0 / num_azimuths), 0.0, 0.0] for i in range(num_azimuths)]

    noData = band.GetNoDataValue()
    local_obs_x = obs_px - xoff
    local_obs_y = obs_py - yoff

    if local_obs_x < 0 or local_obs_x >= regionW or local_obs_y < 0 or local_obs_y >= regionH:
        return [[i * (360.0 / num_azimuths), 0.0, 0.0] for i in range(num_azimuths)]

    obs_elev_val = region[local_obs_y, local_obs_x]
    if noData is not None and _isNoData(obs_elev_val, noData):
        obs_elev = 0.0
    else:
        obs_elev = float(obs_elev_val)

    obs_total = obs_elev + observer_height

    # Grid convergence: rotate geographic azimuth → pixel march direction
    convergence = _grid_convergence(ds, obs_px, obs_py)

    step_px = 1.0
    min_skip_px = min_skip_radius_m / pixel_scale if (pixel_scale > 0 and min_skip_radius_m > 0) else 0
    use_curvature = planet_radius > 0
    profile = []

    # Early termination: max plausible terrain height above observer (meters).
    # If even a peak this tall at the current distance can't beat max_el_angle, stop.
    max_terrain_relief = 10000.0  # 10km — conservative upper bound

    for ai in range(num_azimuths):
        az_deg = ai * (360.0 / num_azimuths)
        az_rad = math.radians(az_deg) + convergence
        # March direction in pixel space, accounting for non-square pixels
        raw_dx = math.sin(az_rad) / px_scale_x
        raw_dy = -math.cos(az_rad) / px_scale_y
        step_len = math.sqrt(raw_dx * raw_dx + raw_dy * raw_dy)
        if step_len < 1e-12:
            step_len = 1e-12
        dx = raw_dx / step_len
        dy = raw_dy / step_len
        m_per_step = 1.0 / step_len  # physical metres per 1-pixel step

        max_el_angle = -90.0
        max_el_dist = 0.0
        max_el_ix = max_el_iy = -1  # [Lunar Navigator] pixel of the highest point (the occluder)
        r = max(step_px, min_skip_px) if min_skip_px > 0 else step_px
        while r <= max_radius_px:
            sx = local_obs_x + dx * r
            sy = local_obs_y + dy * r
            ix = int(round(sx))
            iy = int(round(sy))

            if ix < 0 or ix >= regionW or iy < 0 or iy >= regionH:
                break

            sample = region[iy, ix]
            if noData is not None and _isNoData(float(sample), noData):
                r += max(1.0, math.log2(r + 1))
                continue

            dist_m = r * m_per_step
            if dist_m < 0.001:
                r += max(1.0, math.log2(r + 1))
                continue

            terrain_elev = float(sample)
            # Subtract curvature drop so distant terrain dips below flat-earth
            if use_curvature:
                curvature_drop = (dist_m * dist_m) / (2.0 * planet_radius)
                terrain_elev -= curvature_drop

            elev_angle = math.degrees(
                math.atan2(terrain_elev - obs_total, dist_m)
            )
            if elev_angle > max_el_angle:
                max_el_angle = elev_angle
                max_el_dist = dist_m
                max_el_ix, max_el_iy = ix + xoff, iy + yoff  # [Lunar Navigator]

            # Early termination: if even the tallest possible peak at this
            # distance (after curvature) can't beat current max, stop marching.
            if max_el_angle > -90.0 and dist_m > 1000.0:
                best_possible_elev = max_terrain_relief
                if use_curvature:
                    best_possible_elev -= (dist_m * dist_m) / (2.0 * planet_radius)
                best_possible_angle = math.degrees(
                    math.atan2(best_possible_elev - obs_total, dist_m)
                )
                if best_possible_angle <= max_el_angle:
                    break

            # Logarithmic step: 1px near observer, increasing with distance
            r += max(1.0, math.log2(r + 1))

        profile.append([round(az_deg, 2), round(max_el_angle, 2),
                        round(max_el_dist, 1),
                        max_el_ix, max_el_iy])  # [Lunar Navigator]

    return profile


def _isNoData(value, noData):
    noData = float(noData)
    decPlaces = 1
    if abs(noData) > 1000000000:
        decPlaces = 10
    return abs(value) >= abs(noData / decPlaces) and abs(value) <= abs(noData * decPlaces)


# ---------------------------------------------------------------------------
# [Lunar Navigator] importable wrapper (the argv entry point below is kept as is)
# ---------------------------------------------------------------------------

def compute_horizon_profile(dem, lat, lon, observer_height_m, num_azimuths=720, max_radius_m=5000.0,
                            min_skip_radius_m=0.0, planet_radius=1737400.0):
    """Horizon around (lat, lon) on `dem` (a path/URL, or a dataset already opened with this module's gdal).

    Returns a float array (num_azimuths, 7): azimuth_deg (compass), horizon_el_deg, distance_m, and the highest
    point's x_m, y_m (DEM projection) and lat_deg, lon_deg. Azimuths where no terrain was sampled get
    horizon_el_deg = -90 and NaN for the point.
    """
    ds = gdal.Open(str(dem), GA_ReadOnly) if isinstance(dem, (str, bytes)) or hasattr(dem, "__fspath__") else dem
    band = ds.GetRasterBand(1)
    obs_px, obs_py = latLonToPixel(ds, lat, lon)
    prof = computeHorizonProfile(ds, band, obs_px, obs_py, observer_height_m, num_azimuths, max_radius_m,
                                 min_skip_radius_m, planet_radius)
    out = np.full((len(prof), 7), np.nan)
    gt = ds.GetGeoTransform()
    srs = osr.SpatialReference()
    if int(osgeoversion[0]) >= 3:
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    srs.ImportFromWkt(ds.GetProjection())
    to_geo = osr.CoordinateTransformation(srs, srs.CloneGeogCS())
    for i, row in enumerate(prof):
        out[i, :3] = row[:3]
        if len(row) > 3 and row[3] >= 0:
            x = gt[0] + (row[3] + 0.5) * gt[1] + (row[4] + 0.5) * gt[2]
            y = gt[3] + (row[3] + 0.5) * gt[4] + (row[4] + 0.5) * gt[5]
            plon, plat = to_geo.TransformPoint(x, y)[:2]
            out[i, 3:] = (x, y, plat, (plon + 180.0) % 360.0 - 180.0)
    return out


if __name__ == '__main__':
    raster_path = unquote(sys.argv[1])
    lat = float(sys.argv[2])
    lng = float(sys.argv[3])
    observer_height = float(sys.argv[4])
    num_azimuths = int(sys.argv[5]) if len(sys.argv) > 5 else 360
    max_radius_m = float(sys.argv[6]) if len(sys.argv) > 6 else 5000.0
    min_skip_radius_m = float(sys.argv[7]) if len(sys.argv) > 7 else 0
    planet_radius = float(sys.argv[8]) if len(sys.argv) > 8 else 0

    ds = gdal.Open(raster_path, GA_ReadOnly)
    if ds is None:
        print(json.dumps({"error": True, "message": "Could not open raster"}))
        sys.exit(1)

    band = ds.GetRasterBand(1)
    obs_px, obs_py = latLonToPixel(ds, lat, lng)

    profile = computeHorizonProfile(
        ds, band, obs_px, obs_py, observer_height, num_azimuths, max_radius_m,
        min_skip_radius_m, planet_radius
    )

    print(json.dumps({"horizonProfile": profile}))
