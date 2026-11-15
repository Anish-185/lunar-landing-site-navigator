"""NASA public-domain media for the app and the story site: download once into data/raw/media/, then resize and
compress with rasterio (GDAL's JPEG/WEBP drivers, no extra imaging library).

- Hubble Carina Nebula "Mystic Mountain" (NASA, ESA, M. Livio and the Hubble 20th Anniversary Team, STScI):
  darkened background for the Streamlit app and the story site's nebula layer.
- NASA SVS CGI Moon Kit (LRO LROC colour mosaic with poles, LOLA elevation): the story site's 3D Moon.
- NASA Blue Marble (via NASA SVS 2915): the story site's 3D Earth.
- South-pole hillshade from our own 160 m LOLA DEM (data/derived/dem_80s_160m.tif): parallax terrain layers.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling

from pipeline.fetch_data import download

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "media"
APP_STATIC = ROOT / "app" / "static"
SITE_MEDIA = ROOT / "site" / "public" / "media"

SOURCES = {
    "carina.jpg": "https://images-assets.nasa.gov/image/GSFC_20171208_Archive_e002076/GSFC_20171208_Archive_e002076~large.jpg",
    "moon_color.tif": "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_poles_2k.tif",
    "moon_ldem.jpg": "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/ldem_3_8bit.jpg",
    "earth.png": "https://svs.gsfc.nasa.gov/vis/a000000/a002900/a002915/bluemarble-2048.png",
}


def fetch() -> dict[str, Path]:
    RAW.mkdir(parents=True, exist_ok=True)
    return {name: download(url, RAW / name) for name, url in SOURCES.items()}


def _read_rgb(path: Path, width: int | None = None) -> np.ndarray:
    with rasterio.open(path) as ds:
        h, w = ds.height, ds.width
        if width and width < w:
            h, w = round(h * width / w), width
        a = ds.read(out_shape=(min(ds.count, 3), h, w), resampling=Resampling.average)
    if a.shape[0] == 1:
        a = np.repeat(a, 3, axis=0)
    if a.dtype != np.uint8:
        a = (255 * (a - a.min()) / max(np.ptp(a), 1)).astype(np.uint8)
    return a


def _write(a: np.ndarray, dst: Path, driver: str = "WEBP", quality: int = 70) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    opts = {"QUALITY": quality} if driver in ("WEBP", "JPEG") else {}
    with rasterio.Env(GDAL_PAM_ENABLED="NO", CPL_LOG="/dev/null"):
        with rasterio.open(dst, "w", driver=driver, width=a.shape[2], height=a.shape[1], count=a.shape[0],
                           dtype="uint8", **opts) as out:
            out.write(a)
    return dst


def nebula(src: Path, width: int = 1600, darken: float = 0.55) -> np.ndarray:
    """Darken and cool the Hubble image so text stays readable on top (the colours stay Hubble's)."""
    a = _read_rgb(src, width).astype(float) * darken
    return np.clip(a, 0, 255).astype(np.uint8)


def hillshade(dem: Path, width: int = 1400, az_deg: float = 315.0, alt_deg: float = 8.0) -> np.ndarray:
    """Low-sun hillshade of the 80-90 S LOLA DEM (polar stereographic), the light the pole actually gets."""
    with rasterio.open(dem) as ds:
        scale = width / ds.width
        z = ds.read(1, out_shape=(round(ds.height * scale), width), resampling=Resampling.average,
                    masked=True).astype(float).filled(np.nan)
        px = abs(ds.transform.a) / scale
    gy, gx = np.gradient(np.nan_to_num(z, nan=np.nanmean(z)), px)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(az_deg), np.radians(alt_deg)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    g = np.clip(shade, 0, 1) ** 0.8 * 255
    g[np.isnan(z)] = 0
    return np.repeat(g[None].astype(np.uint8), 3, axis=0)


def heightmap(dem: Path, width: int = 768) -> tuple[np.ndarray, dict]:
    """The 80-90 S LOLA DEM packed for the browser: 16-bit height split over red (high byte) and green (low byte),
    blue = 255 where there is data. The story site relights it in a shader with ray-marched cast shadows."""
    with rasterio.open(dem) as ds:
        scale = width / ds.width
        z = ds.read(1, out_shape=(round(ds.height * scale), width), resampling=Resampling.average,
                    masked=True).astype(float).filled(np.nan)
        px = abs(ds.transform.a) / scale
    lo, hi = float(np.nanmin(z)), float(np.nanmax(z))
    q = np.round((np.nan_to_num(z, nan=lo) - lo) / (hi - lo) * 65535).astype(np.uint16)
    q &= 0xFFF0  # ~3.5 m steps: plenty for 560 m pixels, and the PNG compresses
    rgb = np.stack([q >> 8, q & 255, np.where(np.isnan(z), 0, 255)]).astype(np.uint8)
    return rgb, {"min_m": round(lo, 1), "max_m": round(hi, 1), "px_m": round(px, 1), "width": width}


def build() -> list[Path]:
    src = fetch()
    out = []
    neb = nebula(src["carina.jpg"])
    out.append(_write(neb, APP_STATIC / "nebula.webp", quality=62))
    out.append(_write(neb, SITE_MEDIA / "nebula.webp", quality=62))
    out.append(_write(_read_rgb(src["moon_color.tif"], 2048), SITE_MEDIA / "moon_color.jpg", "JPEG", 82))
    out.append(_write(_read_rgb(src["moon_ldem.jpg"], 1024), SITE_MEDIA / "moon_bump.jpg", "JPEG", 80))
    out.append(_write(_read_rgb(src["earth.png"], 2048), SITE_MEDIA / "earth.jpg", "JPEG", 80))
    hs = hillshade(ROOT / "data" / "derived" / "dem_80s_160m.tif")
    out.append(_write(hs, SITE_MEDIA / "pole_hillshade.webp", quality=70))
    out.append(_write(hillshade(ROOT / "data" / "derived" / "dem_80s_160m.tif", width=900), APP_STATIC / "pole_hillshade.webp",
                      quality=62))  # Map page basemap
    hm, meta = heightmap(ROOT / "data" / "derived" / "dem_80s_160m.tif")
    out.append(_write(hm, SITE_MEDIA / "pole_height.png", "PNG"))
    (SITE_MEDIA / "pole_height.json").write_text(json.dumps(meta))
    out.append(SITE_MEDIA / "pole_height.json")
    return out


if __name__ == "__main__":
    for p in build():
        print(p.relative_to(ROOT), f"{p.stat().st_size / 1e3:.0f} kB")
