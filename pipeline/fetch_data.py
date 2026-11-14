"""Phase 1. Download NAIF generic kernels, PGDA product 90 (LOLA DEMs, slope, error, PSR shapefile)
and PGDA product 69 (AVGVISIB Sun/Earth maps) into data/raw/, and write data/raw/kernels.tm.
Skips existing files and fails loudly on empty or truncated ones.

The 20 m LOLA products (2.7 and 3.8 GB) are not downloaded: navigator.geo.read_window reads
windows of them remotely through GDAL /vsicurl/ range requests (see REMOTE_20M).
URLs come from the product pages https://pgda.gsfc.nasa.gov/products/90 and /products/69.
Large files are fetched as parallel 8 MB byte ranges (resumable), which is much faster on high-latency links.
"""

from __future__ import annotations

import http.client
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
KERNEL_DIR = RAW / "kernels"

NAIF = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels"
PGDA90 = "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp"
PGDA69 = "https://pgda.gsfc.nasa.gov/data/MoonIllumination"

KERNELS = ["lsk/naif0012.tls", "pck/pck00011.tpc", "spk/planets/de440s.bsp", "pck/moon_pa_de440_200625.bpc"]
PGDA90_FILES = ["LDEM_80S_80MPP_ADJ.TIF", "LDSM_80S_80MPP_ADJ.TIF", "LDEM_80S_80MPP_ADJ_ERR.TIF"] + [
    f"LPSR_80S_20MPP_ADJ_1km2.{ext}" for ext in ("SHP", "SHX", "DBF", "PRJ")
]
# The _COG.TIF links on the product page are dead (the server answers 200 with a "Not Found" page),
# so we use the plain GeoTIFFs.
PGDA69_FILES = [f"AVGVISIB_{grid}_201608{body}.TIF" for grid in ("85S_060M", "75S_120M") for body in ("", "_EARTH")]
# USGS Gazetteer of Planetary Nomenclature (public domain): names, centres and diameters of lunar features.
USGS_GAZETTEER = "https://planetarynames.wr.usgs.gov/shapefiles/MOON_nomenclature_center_pts.zip"
REMOTE_20M = {
    "ldem_20m": f"{PGDA90}/LDEM_80S_20MPP_ADJ.TIF",
    "ldsm_20m": f"{PGDA90}/LDSM_80S_20MPP_ADJ.TIF",
    "lderr_20m": f"{PGDA90}/LDEM_80S_20MPP_ADJ_ERR.TIF",
}
# Chandrayaan-3 (69 S) is outside the 80-90 S mosaics: read a window of the 60-90 S 240 m DEM instead.
REMOTE_60S_240M = f"{PGDA90}/LDEM_60S_240MPP_ADJ.TIF"


def latest_moon_fk() -> str:
    """Newest moon_de440_YYMMDD.tf in the NAIF satellites FK directory."""
    listing = urllib.request.urlopen(f"{NAIF}/fk/satellites/", timeout=60).read().decode()
    names = set(re.findall(r"moon_de440_\d{6}\.tf", listing))
    if not names:
        raise RuntimeError("no moon_de440_*.tf found in the NAIF fk/satellites listing")
    return "fk/satellites/" + max(names)


CHUNK = 8 << 20  # parallel byte ranges: on high-latency links each connection is slow, many add up
CONNECTIONS = 8


def _get_range(url: str, a: int, b: int, out: Path, tries: int = 4) -> Path:
    if out.exists() and out.stat().st_size == b - a + 1:
        return out
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={a}-{b}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if r.status == 206 and len(data) == b - a + 1:
                out.write_bytes(data)
                return out
        except (OSError, http.client.HTTPException):  # timeouts, resets, truncated bodies
            if attempt == tries - 1:
                raise
    raise RuntimeError(f"{url}: bytes {a}-{b} came back incomplete {tries} times")


def download(url: str, dest: Path) -> Path:
    """Fetch `url` to `dest` in parallel 8 MB ranges (resumable: finished chunks are kept)."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip  {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)", flush=True)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=0-0"}), timeout=120) as r:
        total = int(r.headers["Content-Range"].split("/")[1]) if r.status == 206 else 0
        if r.headers.get_content_type() == "text/html":  # PGDA serves missing files as a 200 HTML page
            raise RuntimeError(f"{url}: got an HTML page, not a data file (dead link?)")
    if total == 0:
        raise RuntimeError(f"{url}: server reports no size or ignores ranges")
    ranges = [(a, min(a + CHUNK, total) - 1) for a in range(0, total, CHUNK)]
    chunk = lambda i: dest.with_name(f"{dest.name}.part{i:04d}")
    legacy = dest.with_name(dest.name + ".part")  # single-stream partial from an older run: reuse it
    if legacy.exists():
        with open(legacy, "rb") as f:
            for i, (a, b) in enumerate(ranges):
                if a + (b - a + 1) <= legacy.stat().st_size and not chunk(i).exists():
                    f.seek(a)
                    chunk(i).write_bytes(f.read(b - a + 1))
        legacy.unlink()
    done, next_pct = 0, 10
    with ThreadPoolExecutor(max_workers=CONNECTIONS) as pool:
        futures = [pool.submit(_get_range, url, a, b, chunk(i)) for i, (a, b) in enumerate(ranges)]
        for fut in futures:
            fut.result()
            done += 1
            if done * 100 >= next_pct * len(ranges):
                print(f"  {dest.name}: {next_pct}% of {total / 1e6:.0f} MB", flush=True)
                next_pct += 10
    with open(legacy, "wb") as out:
        for i in range(len(ranges)):
            out.write(chunk(i).read_bytes())
    if legacy.stat().st_size != total:
        raise RuntimeError(f"{url}: assembled {legacy.stat().st_size} bytes, expected {total}")
    legacy.rename(dest)
    for i in range(len(ranges)):
        chunk(i).unlink()
    print(f"done  {dest.name} ({total / 1e6:.1f} MB)", flush=True)
    return dest


def write_metakernel(kernel_paths: list[str]) -> Path:
    lines = ["KPL/MK", "", "Generated by pipeline/fetch_data.py", "", "\\begindata", "",
             f"PATH_VALUES  = ( '{KERNEL_DIR}' )", "PATH_SYMBOLS = ( 'K' )", "KERNELS_TO_LOAD = ("]
    lines += [f"  '$K/{Path(p).name}'" for p in kernel_paths] + [")", "", "\\begintext", ""]
    mk = RAW / "kernels.tm"
    mk.write_text("\n".join(lines))
    return mk


def main() -> None:
    kernels = KERNELS + [latest_moon_fk()]
    jobs = [(f"{NAIF}/{k}", KERNEL_DIR / Path(k).name) for k in kernels]
    jobs += [(f"{PGDA90}/{name}", RAW / "pgda90" / name) for name in PGDA90_FILES]
    jobs += [(f"{PGDA69}/{name}", RAW / "pgda69" / name) for name in PGDA69_FILES]
    jobs.append((USGS_GAZETTEER, RAW / "usgs" / Path(USGS_GAZETTEER).name))
    # Slow links: fetch what later steps need first (DEM, small files), the big slope/error grids last.
    jobs.sort(key=lambda job: job[1].name in ("LDSM_80S_80MPP_ADJ.TIF", "LDEM_80S_80MPP_ADJ_ERR.TIF"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda job: download(*job), jobs))
    print(f"metakernel: {write_metakernel(kernels)}")
    print(f"total {sum(p.stat().st_size for p in results) / 1e6:.1f} MB in {len(results)} files")


if __name__ == "__main__":
    sys.exit(main())
