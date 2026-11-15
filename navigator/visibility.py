"""Terrain horizon lookups and how much of the Sun's or Earth's disc clears it (pure NumPy)."""

from __future__ import annotations

import numpy as np


def horizon_at(az_grid, h_grid, az):
    """Horizon elevation (deg) at azimuth(s) `az`, interpolated periodically over a 0-360 grid.

    `h_grid` may be 1-D (one horizon) or 2-D (n_points, n_az): then the result is (n_points, len(az)).
    """
    az = np.asarray(az, float) % 360.0
    h = np.asarray(h_grid, float)
    if h.ndim == 1:
        return np.interp(az, az_grid, h, period=360.0)
    step = 360.0 / h.shape[1]
    pos = az / step
    i0 = np.floor(pos).astype(int) % h.shape[1]
    i1 = (i0 + 1) % h.shape[1]
    w = pos - np.floor(pos)
    return h[:, i0] * (1 - w) + h[:, i1] * w


def nearest_az_index(az_grid, az):
    """Index into a regular azimuth grid of the sample nearest each azimuth (for occluder lookups)."""
    step = 360.0 / len(az_grid)
    return np.rint((np.asarray(az, float) % 360.0) / step).astype(int) % len(az_grid)


def clearance(el, horizon_el):
    """Disc-centre elevation above the terrain horizon (deg); negative = hidden."""
    return np.asarray(el, float) - np.asarray(horizon_el, float)


def disc_fraction(clear_deg, radius_deg):
    """Fraction of a disc of angular radius `radius_deg` above a locally straight horizon, its centre
    `clear_deg` above it: 1 - (acos(c) - c*sqrt(1 - c^2)) / pi with c = clearance / radius, clipped to [-1, 1]."""
    c = np.clip(np.asarray(clear_deg, float) / np.asarray(radius_deg, float), -1.0, 1.0)
    return 1.0 - (np.arccos(c) - c * np.sqrt(1.0 - c * c)) / np.pi


def horizon_sigma_deg(dist_m, sigma_z_m):
    """1-sigma horizon elevation uncertainty (deg) from a terrain height error `sigma_z_m` at the occluder."""
    return np.degrees(np.arctan2(sigma_z_m, np.maximum(np.asarray(dist_m, float), 1.0)))
