"""Solar array power and battery state of charge (illustrative lander presets, docs/METHOD.md)."""

from __future__ import annotations

import numpy as np
import pandas as pd

FLOOR = 0.20  # battery state of charge must stay above 20 %


def array_power(sun_el, eff_sun, array_W: float, panel: str = "vertical"):
    """Array output (W): array_W x geometry x effective sun. 'vertical' = sun-tracking panel standing upright
    (cos el), 'horizontal' = flat panel (sin el)."""
    el = np.radians(np.asarray(sun_el, float))
    geom = np.cos(el) if panel == "vertical" else np.sin(el)
    return array_W * np.clip(geom, 0.0, None) * np.asarray(eff_sun, float)


def battery(t, power_W, load_W: float, capacity_Wh: float, floor: float = FLOOR, soc0: float = 1.0) -> dict:
    """Integrate (power - load) over the samples (forward Euler, step = sample spacing), clipped to [0, capacity].

    `power_W` is (T,) or (n, T) for n landing points at once. Returns soc (fraction, same shape), survives
    (min soc >= floor), min_soc, and first_below (UTC of the first sample under the floor, or NaT)."""
    t = pd.DatetimeIndex(t)
    p = np.atleast_2d(np.asarray(power_W, float))
    dt_h = np.diff(t.as_unit("ns").asi8).astype(float) / 3.6e12 if len(t) > 1 else np.array([])  # any unit -> ns
    dt_h = np.concatenate([dt_h, dt_h[-1:] if len(dt_h) else [1.0]])
    e = np.empty_like(p)
    cur = np.full(p.shape[0], soc0 * capacity_Wh)
    for k in range(p.shape[1]):
        e[:, k] = cur
        cur = np.clip(cur + (p[:, k] - load_W) * dt_h[k], 0.0, capacity_Wh)
    soc = e / capacity_Wh
    below = soc < floor
    first = np.where(below.any(axis=1), below.argmax(axis=1), -1)
    first_t = pd.DatetimeIndex([t[i] if i >= 0 else pd.NaT for i in first])
    squeeze = np.ndim(power_W) == 1
    return {
        "soc": soc[0] if squeeze else soc,
        "min_soc": soc.min(axis=1)[0] if squeeze else soc.min(axis=1),
        "survives": (~below.any(axis=1))[0] if squeeze else ~below.any(axis=1),
        "first_below": first_t[0] if squeeze else first_t,
    }
