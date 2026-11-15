"""Phase 9 thermal layer: Diviner PRP fixed-width parsing and the site 'Thermal' line."""

import numpy as np
import pytest

from navigator import scores
from pipeline import thermal


def _row(lon, lat, tavg, tmax, ice):
    """One 210-byte PRP record laid out at the byte offsets of dlre_prp.fmt."""
    buf = [" "] * 208
    def put(start, width, text):
        s = f"{text:>{width}}"
        buf[start:start + width] = list(s)
    for k in range(9):  # triangle vertices: irrelevant here
        put(14 * k, 12, f"{k:.3f}")
    put(126, 15, f"{lon:.6f}")
    put(143, 15, f"{lat:.6f}")
    put(160, 15, "0.0")
    put(177, 8, f"{tavg:.2f}")
    put(187, 8, f"{tmax:.2f}")
    put(197, 11, f"{ice:.4f}")
    return "".join(buf) + "\r\n"


def test_read_prp_parses_columns_and_filters_latitude(tmp_path):
    p = tmp_path / "prp.tab"
    p.write_text("HEADER".ljust(208) + "\r\n" + _row(350.0, -85.5, 95.1, 105.2, 0.05) + _row(10.0, -70.0, 200, 300, 1)
                 + _row(120.0, -89.0, 60.0, -9999.0, -1))
    df = thermal.read_prp(p)
    assert len(df) == 2  # the 70 S row is dropped
    first = df.iloc[0]
    assert first["lon"] == pytest.approx(-10.0) and first["lat"] == pytest.approx(-85.5)
    assert first["tmax"] == pytest.approx(105.2) and first["ice_depth"] == pytest.approx(0.05)
    assert np.isnan(df.iloc[1]["tmax"]) and np.isnan(df.iloc[1]["ice_depth"])  # fill values -> NaN


def test_thermal_reason():
    assert scores.thermal_reason(None) is None
    cold = scores.thermal_reason({"tmax_k": 90.0, "tavg_k": 50.0, "cold_trap_share": 1.0})
    assert "Cold trap" in cold and "90 K" in cold
    warm = scores.thermal_reason({"tmax_k": 250.0, "tavg_k": 120.0, "cold_trap_share": 0.1})
    assert "10%" in warm and "Cold trap:" not in warm
