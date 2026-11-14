"""Phase 2. Hourly Sun/Earth topocentric az/el/range for every catalog site -> data/derived/ephem/<site_id>.parquet,
and validation against JPL Horizons -> data/derived/validation_horizons.csv.

The maths is navigator.engine.sun_earth_azel (spiceypy.azlcpo), the same function the app uses for custom sites.
Horizons responses are cached in tests/fixtures/horizons.csv so validation and tests run offline;
`fetch_horizons_fixtures()` refreshes them (network; astroquery).
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from navigator import engine
from pipeline.sites import load_sites, site_by_id

ROOT = Path(__file__).resolve().parents[1]
RAW_KERNELS = ROOT / "data" / "raw" / "kernels"
EPHEM_DIR = ROOT / "data" / "derived" / "ephem"
FIXTURE = ROOT / "tests" / "fixtures" / "horizons.csv"
VALIDATION_CSV = ROOT / "data" / "derived" / "validation_horizons.csv"

# Inclusive UTC date ranges: Chandrayaan-3 hindcast, IM-1, IM-2 + Blue Ghost 1, planning horizon.
WINDOWS = [("2023-08-01", "2023-09-30"), ("2024-02-15", "2024-03-31"),
           ("2025-02-20", "2025-03-31"), ("2026-11-01", "2028-12-31")]

# Validation: Apollo 11, Shackleton rim (Chang'e-7 target), Malapert x 20 epochs over 2027; Athena x 5 on landing day.
VALIDATION_SITES = ["apollo_11", "change_7_target", "artemis_malapert_massif"]
VALIDATION_EPOCHS = pd.date_range("2027-01-05 03:00", periods=20, freq="433h", tz="UTC")  # ~18 days apart, hour varies
ATHENA_EPOCHS = pd.DatetimeIndex(["2025-03-06 00:00", "2025-03-06 06:00", "2025-03-06 12:00",
                                  "2025-03-06 17:28", "2025-03-06 23:00"], tz="UTC")
HORIZONS_IDS = {"sun": "10", "earth": "399"}


def hourly_utc() -> pd.DatetimeIndex:
    parts = [pd.date_range(a, pd.Timestamp(b) + pd.Timedelta(hours=23), freq="h", tz="UTC") for a, b in WINDOWS]
    return parts[0].append(parts[1:])


def ship_kernels() -> None:
    """Copy the kernels the app needs from data/raw/ into data/derived/kernels/ (the app has no network)."""
    engine.KERNEL_DIR.mkdir(parents=True, exist_ok=True)
    for name in engine.KERNELS:
        src, dst = RAW_KERNELS / name, engine.KERNEL_DIR / name
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dst)


def build_site(site: dict, times: pd.DatetimeIndex) -> Path:
    df = engine.sun_earth_azel(site["lat"], site["lon"], times)
    df[engine.COLUMNS[1:]] = df[engine.COLUMNS[1:]].astype("float32")
    out = EPHEM_DIR / f"{site['id']}.parquet"
    df.to_parquet(out, index=False, compression="zstd")
    return out


def build_all(n_jobs: int = -1) -> float:
    """Ephemeris for every catalog site, in parallel. Returns the wall time in seconds."""
    ship_kernels()
    EPHEM_DIR.mkdir(parents=True, exist_ok=True)
    times, t0 = hourly_utc(), time.time()
    Parallel(n_jobs=n_jobs)(delayed(build_site)(s, times) for s in load_sites())
    return time.time() - t0


# --- validation against JPL Horizons ---

def _validation_plan() -> list[tuple[str, pd.DatetimeIndex]]:
    return [(s, VALIDATION_EPOCHS) for s in VALIDATION_SITES] + [("im2_actual", ATHENA_EPOCHS)]


def fetch_horizons_fixtures(path: Path = FIXTURE) -> pd.DataFrame:
    """Query JPL Horizons (network) for apparent AZ/EL of the Sun and Earth at each validation site and epoch."""
    from astroquery.jplhorizons import Horizons

    rows = []
    for site_id, epochs in _validation_plan():
        site = site_by_id(site_id)
        jd = epochs.tz_convert(None).to_julian_date().tolist()  # UTC Julian dates
        for body, hid in HORIZONS_IDS.items():
            eph = Horizons(id=hid, location={"lon": site["lon"], "lat": site["lat"], "elevation": 0.0, "body": 301},
                           epochs=jd).ephemerides(quantities="4", refraction=False, extra_precision=True,
                                                  optional_settings={"TIME_TYPE": "UT", "TLIST_TYPE": "JD"})
            # Independent of our JD conversion: Horizons' own calendar strings must equal the requested UTC epochs.
            got = pd.to_datetime(list(eph["datetime_str"]), format="%Y-%b-%d %H:%M:%S.%f", utc=True)
            if len(got) != len(epochs) or np.max(np.abs((got - epochs).total_seconds())) > 0.01:
                raise RuntimeError(f"Horizons epochs {list(got[:2])} differ from requested {list(epochs[:2])}")
            for requested, row in zip(epochs, eph):
                rows.append({"site_id": site_id, "body": body, "utc": requested.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "horizons_datetime": row["datetime_str"], "horizons_jd": float(row["datetime_jd"]),
                             "az": float(row["AZ"]), "el": float(row["EL"])})
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def horizons_residuals(fixture: Path = FIXTURE) -> pd.DataFrame:
    """Our az/el minus Horizons' at every cached epoch. Azimuth residual is wrapped and scaled by cos(el)
    (the on-sky separation along the horizon); `sep` is the total angular separation in degrees."""
    ref = pd.read_csv(fixture)
    out = []
    for site_id, group in ref.groupby("site_id", sort=False):
        site = site_by_id(site_id)
        ours = engine.sun_earth_azel(site["lat"], site["lon"], group["utc"].unique())
        ours["utc"] = ours["utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        for body in ("sun", "earth"):
            m = group[group["body"] == body].merge(ours[["utc", f"{body}_az", f"{body}_el"]], on="utc")
            m = m.rename(columns={"az": "horizons_az", "el": "horizons_el", f"{body}_az": "our_az", f"{body}_el": "our_el"})
            m["d_az"] = (m["our_az"] - m["horizons_az"] + 180) % 360 - 180
            m["d_el"] = m["our_el"] - m["horizons_el"]
            m["d_az_cos_el"] = m["d_az"] * np.cos(np.radians(m["horizons_el"]))
            m["sep"] = np.degrees(_separation(m["our_az"], m["our_el"], m["horizons_az"], m["horizons_el"]))
            out.append(m)
    return pd.concat(out, ignore_index=True)


def _separation(az1, el1, az2, el2):
    a1, e1, a2, e2 = (np.radians(np.asarray(v, dtype=float)) for v in (az1, el1, az2, el2))
    c = np.sin(e1) * np.sin(e2) + np.cos(e1) * np.cos(e2) * np.cos(a1 - a2)
    return np.arccos(np.clip(c, -1, 1))


def write_validation() -> pd.DataFrame:
    res = horizons_residuals()
    res.to_csv(VALIDATION_CSV, index=False, float_format="%.6f")
    return res
