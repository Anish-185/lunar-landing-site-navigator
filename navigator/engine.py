"""Sun and Earth topocentric azimuth, elevation and range for a point on the Moon (SPICE azlcpo), plus the
site/timeline layer the app and the story export share.

`sun_earth_azel` serves both the offline pipeline (catalog sites) and the app (custom sites at runtime). It reads the
kernels shipped in data/derived/kernels/, so it needs no network. Conventions follow CLAUDE.md: UTC in, MOON_ME
frame, LT+S aberration, compass azimuth (0 = local north, 90 = east), degrees out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import spiceypy as spice
from spiceypy.utils.exceptions import NotFoundError

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
KERNEL_DIR = DERIVED / "kernels"
KERNELS = ("naif0012.tls", "pck00011.tpc", "de440s.bsp", "moon_pa_de440_200625.bpc", "moon_de440_250416.tf")
MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 696000.0
EARTH_RADIUS_KM = 6371.0
COLUMNS = ["utc", "sun_az", "sun_el", "sun_range_km", "earth_az", "earth_el", "earth_range_km"]
MASTS = (1.0, 2.0, 5.0, 10.0, 15.0, 20.0)
N_AZ = 720
COARSE_DEM = DERIVED / "dem_80s_160m.tif"
FAR_M = 200000.0


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


# --- sites: catalog (precomputed horizons) and custom lat/lon (horizon from the shipped 160 m DEM) ---

@dataclass
class Site:
    id: str
    name: str
    lat: float
    lon: float
    horizon_source: str
    az: np.ndarray                 # (720,) compass azimuth, deg
    masts: np.ndarray              # (6,) mast heights, m
    el: np.ndarray                 # (6, 720) horizon elevation per mast, deg
    dist: np.ndarray               # (6, 720) distance to the occluder, m
    occ_name: np.ndarray           # (6, 720) named feature of the occluder ('' = unnamed)
    occ_relation: np.ndarray       # (6, 720)
    occ_x: np.ndarray              # (6, 720) polar stereographic x/y of the occluder, m
    occ_y: np.ndarray
    group: str = "custom"
    lander: str = "precision_100m"
    note: str = ""
    source_url: str = ""
    landing_utc: str | None = None
    target: dict | None = None
    custom: bool = False
    meta: dict = field(default_factory=dict)

    def mast_row(self, mast_m: float) -> int:
        return int(np.argmin(np.abs(self.masts - mast_m)))

    def horizon(self, mast_m: float) -> np.ndarray:
        """Horizon elevation (720,) at any mast height, interpolated linearly between the computed masts."""
        m = float(np.clip(mast_m, self.masts[0], self.masts[-1]))
        j = int(np.clip(np.searchsorted(self.masts, m) - 1, 0, len(self.masts) - 2))
        w = (m - self.masts[j]) / (self.masts[j + 1] - self.masts[j])
        return self.el[j] * (1 - w) + self.el[j + 1] * w

    @property
    def has_terrain(self) -> bool:
        return self.horizon_source != "smooth_sphere"


@lru_cache(maxsize=1)
def catalog() -> tuple[dict, ...]:
    from pipeline.sites import load_sites

    return tuple(load_sites())


@lru_cache(maxsize=1)
def landers() -> dict:
    from pipeline.sites import load_landers

    return load_landers()


@lru_cache(maxsize=64)
def load_site(site_id: str) -> Site:
    meta = next(s for s in catalog() if s["id"] == site_id)
    with np.load(DERIVED / "horizons" / f"{site_id}.npz") as z:
        return Site(id=site_id, name=meta["name"], lat=float(meta["lat"]), lon=float(meta["lon"]),
                    horizon_source=str(z["horizon_source"]), az=z["az"], masts=z["masts"],
                    el=z["el"].astype(float), dist=z["dist"].astype(float), occ_name=z["name"],
                    occ_relation=z["relation"], occ_x=z["x"].astype(float), occ_y=z["y"].astype(float),
                    group=meta["group"], lander=meta.get("lander", "precision_100m"), note=meta.get("note", ""),
                    source_url=meta.get("source_url", ""), landing_utc=meta.get("landing_utc"),
                    target=meta.get("target"), meta=dict(meta))


@lru_cache(maxsize=1)
def features() -> pd.DataFrame:
    return pd.read_csv(DERIVED / "lunar_features.csv")


@lru_cache(maxsize=32)
def custom_site(lat: float, lon: float, name: str = "Custom site") -> Site:
    """Horizon for any lat/lon in 80-90 S from the shipped 160 m DEM (vendored MMGIS HorizonProfile on the
    rasterio/pyproj stand-ins; no GDAL). Coarser than catalog sites; the UI says so."""
    from navigator import geo
    from vendor.mmgis_sightline import HorizonProfile as hp

    if lat > -80.0:
        raise ValueError("custom sites must lie in 80-90 S (the shipped DEM's coverage)")
    rows = [hp.compute_horizon_profile(str(COARSE_DEM), lat, lon, m, N_AZ, FAR_M, 0.0, MOON_RADIUS_KM * 1000)
            for m in MASTS]
    el = np.stack([r[:, 1] for r in rows])
    names, rels = zip(*(geo.name_points(r[:, 5], r[:, 6], features()) for r in rows))
    return Site(id=f"custom_{lat:.4f}_{lon:.4f}", name=name, lat=lat, lon=lon, horizon_source="dem_80s_160m",
                az=rows[0][:, 0], masts=np.array(MASTS), el=el, dist=np.stack([r[:, 2] for r in rows]),
                occ_name=np.stack(names), occ_relation=np.stack(rels), occ_x=np.stack([r[:, 3] for r in rows]),
                occ_y=np.stack([r[:, 4] for r in rows]), custom=True,
                note="Custom site: coarser terrain (160 m) than catalog sites.")


@lru_cache(maxsize=32)
def load_tile(site_id: str) -> dict | None:
    path = DERIVED / "tiles" / f"{site_id}.npz"
    if not path.exists():
        return None
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


@lru_cache(maxsize=32)
def _parquet(site_id: str) -> pd.DataFrame:
    return pd.read_parquet(DERIVED / "ephem" / f"{site_id}.parquet").set_index("utc")


def ephemeris(site: Site, start, end, freq: str = "1h") -> pd.DataFrame:
    """Hourly Sun/Earth az/el/range over [start, end): the precomputed table when it covers the range (catalog
    sites), otherwise SPICE at runtime (custom sites, or dates outside the precomputed windows)."""
    times = pd.date_range(pd.Timestamp(start).tz_convert("UTC").floor(freq), pd.Timestamp(end).tz_convert("UTC"),
                          freq=freq, inclusive="left")
    if not site.custom and freq == "1h":
        tab = _parquet(site.id)
        hit = tab.reindex(times)
        if not hit.isna().any().any():
            return hit.astype(float).reset_index(names="utc")
    return sun_earth_azel(site.lat, site.lon, times)


@lru_cache(maxsize=8)
def _dsn_year(year: int) -> pd.Series:
    from navigator import comms

    times = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="1h", inclusive="left", tz="UTC")
    return comms.dsn_in_view(times)["any"]


def dsn_any(times) -> np.ndarray:
    """DSN-in-view flag (any complex sees the Moon >= 10 deg) at whole-hour UTC times, cached per calendar year
    so the Slip Replanner's many scenarios cost one Skyfield run per year."""
    t = pd.DatetimeIndex(times)
    s = pd.concat([_dsn_year(y) for y in sorted(set(t.year))])
    return s.reindex(t.floor("1h")).fillna(False).to_numpy(bool)


def timeline(site: Site, start, days: float, mast_m: float = 2.0, lander: dict | None = None,
             thresholds: dict | None = None, eph: pd.DataFrame | None = None) -> pd.DataFrame:
    """Everything per hour for one scenario: Sun/Earth clearance, visible disc fractions, eclipse, effective sun,
    comm band, DSN, link, array power and battery state of charge."""
    from navigator import comms, eclipse, power, visibility

    start = pd.Timestamp(start)
    start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
    lander = lander or landers()[site.lander]
    df = eph.copy() if eph is not None else ephemeris(site, start, start + pd.Timedelta(days=days))
    h = site.horizon(mast_m)
    for body, rad in (("sun", sun_radius_deg), ("earth", earth_radius_deg)):
        df[f"{body}_r"] = rad(df[f"{body}_range_km"])
        df[f"{body}_h"] = visibility.horizon_at(site.az, h, df[f"{body}_az"])
        df[f"{body}_clear"] = visibility.clearance(df[f"{body}_el"], df[f"{body}_h"])
        df[f"{body}_frac"] = visibility.disc_fraction(df[f"{body}_clear"], df[f"{body}_r"])
        df[f"{body}_occ"] = visibility.nearest_az_index(site.az, df[f"{body}_az"])
    sep = eclipse.angular_separation(df["sun_az"], df["sun_el"], df["earth_az"], df["earth_el"])
    df["eclipse"] = eclipse.overlap_fraction(df["sun_r"], df["earth_r"], sep)
    df["eff_sun"] = eclipse.effective_sun(df["sun_frac"], df["eclipse"])
    df["sunlit"] = df["eff_sun"] > 0
    df["earth_visible"] = df["earth_frac"] > 0
    df["band"] = comms.band(df["earth_clear"], thresholds)
    df["dsn"] = dsn_any(df["utc"])
    df["link"] = comms.link_usable(df["band"], df["dsn"])
    df["both"] = df["sunlit"] & df["link"]
    df["power_W"] = power.array_power(df["sun_el"], df["eff_sun"], lander["array_W"], lander["panel"])
    bat = power.battery(df["utc"], df["power_W"], lander["load_W"], lander["battery_Wh"])
    df["soc"] = bat["soc"]
    df.attrs.update({"site_id": site.id, "mast_m": mast_m, "lander": lander, "start": start, "days": days})
    return df
