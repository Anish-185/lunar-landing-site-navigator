"""Direct-to-Earth link quality: Earth clearance bands (multipath) and Deep Space Network visibility (Skyfield).

Thresholds are assumptions, not a link budget (docs/METHOD.md). Low Earth elevation over the lunar horizon gives
multipath and terrain-diffraction losses at the south pole (JPL south-pole communication studies cited there).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

KERNEL = Path(__file__).resolve().parents[1] / "data" / "derived" / "kernels" / "de440s.bsp"
BANDS = ("none", "poor", "marginal", "good")
DEFAULT_THRESHOLDS = {"good": 5.0, "marginal": 2.0, "poor": 0.0}  # Earth clearance (deg), illustrative
DSN = {  # lat, lon (deg), from the DSN station positions
    "Goldstone": (35.4267, -116.8900),
    "Madrid": (40.4314, -4.2481),
    "Canberra": (-35.4014, 148.9817),
}
DSN_MIN_EL = 10.0


def band(clear_deg, thresholds: dict | None = None) -> np.ndarray:
    """Quality band per sample from Earth clearance (deg): good >= 5, marginal 2-5, poor 0-2, none < 0."""
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    c = np.asarray(clear_deg, float)
    idx = (c >= th["poor"]).astype(int) + (c >= th["marginal"]) + (c >= th["good"])
    return np.asarray(BANDS)[idx]


def band_rank(b) -> np.ndarray:
    """0 (none) .. 3 (good) for band labels."""
    lookup = {name: i for i, name in enumerate(BANDS)}
    return np.array([lookup[x] for x in np.atleast_1d(b)], dtype=int)


@lru_cache(maxsize=1)
def _sky():
    from skyfield.api import load, load_file

    eph = load_file(str(KERNEL))
    return load.timescale(builtin=True), eph


def dsn_moon_elevation(utc) -> pd.DataFrame:
    """Moon elevation (deg) above each DSN complex's horizon, with Skyfield and the shipped DE440s kernel."""
    from skyfield.api import wgs84

    ts, eph = _sky()
    t = pd.DatetimeIndex(pd.to_datetime(utc, utc=True))
    tt = ts.from_datetimes(t.to_pydatetime())
    out = {}
    for name, (lat, lon) in DSN.items():
        station = eph["earth"] + wgs84.latlon(lat, lon)
        alt, _, _ = station.at(tt).observe(eph["moon"]).apparent().altaz()
        out[name] = alt.degrees
    return pd.DataFrame(out, index=t)


def dsn_in_view(utc, min_el: float = DSN_MIN_EL) -> pd.DataFrame:
    el = dsn_moon_elevation(utc)
    view = el >= min_el
    view["any"] = view.any(axis=1)
    return view


def link_usable(bands, dsn_any) -> np.ndarray:
    """Usable direct-to-Earth link: band marginal or better AND at least one DSN complex sees the Moon."""
    b = np.asarray(bands)
    return np.isin(b, ("marginal", "good")) & np.asarray(dsn_any, bool)
