"""Rises, sets, continuous windows and countdowns from a sampled clearance series (pandas + NumPy)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _seconds(t) -> np.ndarray:
    t = pd.DatetimeIndex(t)
    return t.as_unit("ns").asi8 / 1e9  # pandas 3 may store s/ms/us: normalise first


def crossings(t, value) -> pd.DataFrame:
    """Sign changes of `value` (e.g. clearance in deg) refined by linear interpolation.

    Returns columns utc (UTC timestamps) and kind ("rise": value goes from < 0 to >= 0, "set": the reverse)."""
    t = pd.DatetimeIndex(t)
    v = np.asarray(value, float)
    up = v >= 0
    i = np.flatnonzero(up[1:] != up[:-1])
    if len(i) == 0:
        return pd.DataFrame({"utc": pd.DatetimeIndex([], tz="UTC"), "kind": pd.Series([], dtype=str)})
    s = _seconds(t)
    frac = v[i] / (v[i] - v[i + 1])
    when = s[i] + frac * (s[i + 1] - s[i])
    return pd.DataFrame({"utc": pd.to_datetime(when, unit="s", utc=True).round("s"),
                         "kind": np.where(up[i + 1], "rise", "set")})


def windows(t, mask) -> pd.DataFrame:
    """Continuous runs where `mask` is True: start, end (time of the first False sample after it, or the last
    sample) and duration_h. Sample-resolution; refine edges with `crossings` when a clearance is available."""
    t = pd.DatetimeIndex(t)
    m = np.asarray(mask, bool)
    if len(m) == 0:
        return pd.DataFrame(columns=["start", "end", "duration_h"])
    edges = np.diff(np.concatenate([[0], m.astype(int), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    df = pd.DataFrame({"start": t[starts], "end": t[np.minimum(ends, len(t) - 1)]})
    df["duration_h"] = (df["end"] - df["start"]).dt.total_seconds() / 3600.0
    return df


def longest(t, mask) -> dict:
    """Longest True run: {'hours', 'start', 'end'} (hours 0 and NaT if none)."""
    w = windows(t, mask)
    if w.empty:
        return {"hours": 0.0, "start": pd.NaT, "end": pd.NaT}
    r = w.loc[w["duration_h"].idxmax()]
    return {"hours": float(r["duration_h"]), "start": r["start"], "end": r["end"]}


def next_event(t, value, now, kind: str):
    """First `kind` ("rise" | "set") crossing at or after `now`, or NaT."""
    c = crossings(t, value)
    c = c[(c["kind"] == kind) & (c["utc"] >= pd.Timestamp(now))]
    return c["utc"].iloc[0] if len(c) else pd.NaT


def countdown(t, value, now, kind: str, sigma=None) -> dict:
    """Time to the next `kind` event, with an uncertainty window from shifting the horizon by +/- sigma (deg).

    `value` is clearance (deg). Raising the horizon makes sets earlier and rises later. Returns
    {'utc', 'hours', 'earliest', 'latest'} (NaT/NaN where no event is found in the series)."""
    now = pd.Timestamp(now)
    when = next_event(t, value, now, kind)
    out = {"utc": when, "hours": (when - now).total_seconds() / 3600 if pd.notna(when) else np.nan,
           "earliest": when, "latest": when}
    if sigma is not None:
        v = np.asarray(value, float)
        a = next_event(t, v - sigma, now, kind)  # horizon higher
        b = next_event(t, v + sigma, now, kind)  # horizon lower
        cand = pd.Series([x for x in (when, a, b) if pd.notna(x)], dtype="datetime64[ns, UTC]")
        if len(cand):
            out["earliest"], out["latest"] = cand.min(), cand.max()
    return out


def format_hours(h: float) -> str:
    """'3 d 4 h', '7 h', '25 min' for countdown chips."""
    if h is None or not np.isfinite(h):
        return "beyond window"
    if h >= 48:
        return f"{int(h // 24)} d {int(round(h % 24))} h"
    if h >= 1:
        return f"{h:.0f} h"
    return f"{h * 60:.0f} min"
