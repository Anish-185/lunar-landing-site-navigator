"""Load and validate the site catalog (sites.yaml) and lander presets (landers.yaml)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
GROUPS = {"artemis_region", "clps", "international", "apollo"}
LANDER_NUMBERS = ("cruise_days", "ellipse_sigma_m", "array_W", "battery_Wh", "load_W")
ILLUSTRATIVE = "illustrative - edit me"
POLAR_DEM_LAT = -80.0  # the PGDA 90 south polar DEMs cover 80-90 S


def _check_latlon(where: str, lat, lon) -> None:
    if not (isinstance(lat, (int, float)) and -90 <= lat <= 90):
        raise ValueError(f"{where}: lat {lat!r} not in [-90, 90]")
    if not (isinstance(lon, (int, float)) and -180 <= lon < 180):
        raise ValueError(f"{where}: lon {lon!r} not in [-180, 180) east-positive")


def load_sites(path: Path = HERE / "sites.yaml") -> list[dict]:
    sites = yaml.safe_load(path.read_text())["sites"]
    seen = set()
    for s in sites:
        where = f"sites.yaml {s.get('id', '?')}"
        missing = {"id", "name", "group", "lat", "lon", "source_url", "note"} - s.keys()
        if missing:
            raise ValueError(f"{where}: missing {sorted(missing)}")
        if s["id"] in seen or not s["id"].replace("_", "").isalnum() or s["id"] != s["id"].lower():
            raise ValueError(f"{where}: id must be a unique lowercase slug")
        seen.add(s["id"])
        if s["group"] not in GROUPS:
            raise ValueError(f"{where}: group {s['group']!r} not in {sorted(GROUPS)}")
        if not s["source_url"].startswith("https://"):
            raise ValueError(f"{where}: source_url must be an https URL")
        _check_latlon(where, s["lat"], s["lon"])
        if "target" in s:
            _check_latlon(f"{where} target", s["target"]["lat"], s["target"]["lon"])
        if "landing_utc" in s:
            if not str(s["landing_utc"]).endswith("Z"):
                raise ValueError(f"{where}: landing_utc must be ISO 8601 UTC ending in Z")
            datetime.fromisoformat(str(s["landing_utc"]).replace("Z", "+00:00"))
        if s.get("lander") not in _lander_keys():
            raise ValueError(f"{where}: lander {s.get('lander')!r} not in landers.yaml")
        s["in_polar_dem"] = s["lat"] <= POLAR_DEM_LAT
    return sites


def _lander_keys() -> set[str]:
    return set(yaml.safe_load((HERE / "landers.yaml").read_text())["landers"])


def load_landers(path: Path = HERE / "landers.yaml") -> dict[str, dict]:
    landers = yaml.safe_load(path.read_text())["landers"]
    for key, lander in landers.items():
        where = f"landers.yaml {key}"
        missing = {"name", "panel", "sources", *LANDER_NUMBERS} - lander.keys()
        if missing:
            raise ValueError(f"{where}: missing {sorted(missing)}")
        if lander["panel"] not in ("vertical", "horizontal"):
            raise ValueError(f"{where}: panel must be vertical or horizontal")
        for field in LANDER_NUMBERS:
            if not (isinstance(lander[field], (int, float)) and lander[field] > 0):
                raise ValueError(f"{where}: {field} must be a positive number")
            src = lander["sources"].get(field, "")
            if src != ILLUSTRATIVE and "https://" not in src:
                raise ValueError(f"{where}: {field} needs a cited source (with URL) or exactly '{ILLUSTRATIVE}'")
    return landers


def site_by_id(site_id: str) -> dict:
    for s in load_sites():
        if s["id"] == site_id:
            return s
    raise KeyError(site_id)
