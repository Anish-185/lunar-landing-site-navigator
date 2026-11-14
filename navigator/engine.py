"""Sun and Earth topocentric azimuth, elevation and range for a point on the Moon (SPICE azlcpo).

One function serves both the offline pipeline (catalog sites) and the app (custom sites at runtime). It reads the
kernels shipped in data/derived/kernels/, so it needs no network. Conventions follow CLAUDE.md: UTC in, MOON_ME
frame, LT+S aberration, compass azimuth (0 = local north, 90 = east), degrees out.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import spiceypy as spice
from spiceypy.utils.exceptions import NotFoundError

KERNEL_DIR = Path(__file__).resolve().parents[1] / "data" / "derived" / "kernels"
KERNELS = ("naif0012.tls", "pck00011.tpc", "de440s.bsp", "moon_pa_de440_200625.bpc", "moon_de440_250416.tf")
MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 696000.0
EARTH_RADIUS_KM = 6371.0
COLUMNS = ["utc", "sun_az", "sun_el", "sun_range_km", "earth_az", "earth_el", "earth_range_km"]


def load_kernels(kernel_dir: Path = KERNEL_DIR) -> None:
    """Furnish the kernels once per process (safe to call repeatedly, also after a kclear)."""
    for name in KERNELS:
        path = str(kernel_dir / name)
        try:
            spice.kinfo(path)
        except NotFoundError:
            spice.furnsh(path)


def sun_earth_azel(lat_deg: float, lon_deg: float, utc, height_m: float = 0.0) -> pd.DataFrame:
    """Sun and Earth az/el (degrees) and range (km) seen from (lat, lon, height above the 1737.4 km sphere).

    `utc`: anything pandas turns into timestamps (naive values are taken as UTC).
    """
    load_kernels()
    times = pd.DatetimeIndex(pd.to_datetime(utc, utc=True))
    ets = np.atleast_1d(spice.str2et(list(times.strftime("%Y-%m-%dT%H:%M:%S.%f"))))
    obspos = spice.latrec(MOON_RADIUS_KM + height_m / 1000.0, np.radians(lon_deg), np.radians(lat_deg))
    out = np.empty((len(ets), 6))
    for i, et in enumerate(ets):
        for j, target in enumerate(("SUN", "EARTH")):
            state, _ = spice.azlcpo("ELLIPSOID", target, et, "LT+S", False, True, obspos, "MOON", "MOON_ME")
            out[i, 3 * j: 3 * j + 3] = state[:3]  # range (km), azimuth (rad), elevation (rad)
    return pd.DataFrame({
        "utc": times,
        "sun_az": np.degrees(out[:, 1]), "sun_el": np.degrees(out[:, 2]), "sun_range_km": out[:, 0],
        "earth_az": np.degrees(out[:, 4]), "earth_el": np.degrees(out[:, 5]), "earth_range_km": out[:, 3],
    })


def angular_radius_deg(range_km, radius_km: float):
    """Apparent angular radius (degrees) of a sphere of `radius_km` seen from `range_km`."""
    return np.degrees(np.arcsin(radius_km / np.asarray(range_km)))


def sun_radius_deg(range_km):
    return angular_radius_deg(range_km, SUN_RADIUS_KM)


def earth_radius_deg(range_km):
    return angular_radius_deg(range_km, EARTH_RADIUS_KM)
