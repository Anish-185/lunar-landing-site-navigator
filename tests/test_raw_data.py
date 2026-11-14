"""data/raw/ integrity: every downloaded file is the format it claims (PGDA answers dead links with a
200 HTML page), and the generated metakernel loads with the MOON_ME frame. Skips what is not downloaded."""

from pathlib import Path

import pytest

from pipeline import fetch_data as fd

MAGIC = {
    ".tif": (b"II*\x00", b"II+\x00", b"MM\x00*", b"MM\x00+"),  # TIFF / BigTIFF
    ".shp": (b"\x00\x00\x27\x0a",), ".shx": (b"\x00\x00\x27\x0a",),
    ".bsp": (b"DAF/SPK",), ".bpc": (b"DAF/PCK",),
    ".tls": (b"KPL/LSK",), ".tpc": (b"KPL/PCK",), ".tf": (b"KPL/FK",),
    ".dbf": (b"\x03",), ".prj": (b"PROJCS", b"GEOGCS"), ".zip": (b"PK\x03\x04",),
}


def _downloaded() -> list[Path]:
    files = [p for p in fd.RAW.rglob("*") if p.is_file() and p.suffix.lower() in MAGIC]
    return files or [pytest.param(None, marks=pytest.mark.skip(reason="nothing downloaded (make data)"))]


@pytest.mark.parametrize("path", _downloaded(), ids=lambda p: p.name if p else "none")
def test_file_has_expected_magic_bytes(path):
    head = path.read_bytes()[:16]
    assert head.startswith(MAGIC[path.suffix.lower()]), f"{path.name} starts with {head!r} (an HTML error page?)"


def test_metakernel_loads_moon_me():
    spice = pytest.importorskip("spiceypy")
    mk = fd.RAW / "kernels.tm"
    if not mk.exists():
        pytest.skip("kernels.tm not written yet (make data)")
    spice.kclear()
    try:
        spice.furnsh(str(mk))
        assert spice.namfrm("MOON_ME") != 0
        et = spice.str2et("2026-11-15T00:00:00")
        pos, _ = spice.spkpos("SUN", et, "MOON_ME", "LT+S", "MOON")
        assert 1.3e8 < (pos @ pos) ** 0.5 < 1.6e8  # ~1 AU in km
    finally:
        spice.kclear()
