"""Phase 5 engine: visibility, eclipse, events, comms, power, scores, landing (synthetic inputs + a few real sites)."""

import numpy as np
import pandas as pd
import pytest

from navigator import comms, eclipse, engine, events, landing, power, scores, visibility

AZ = np.arange(720) * 0.5


# --- visibility ---

def test_disc_fraction_edges_and_half():
    f = visibility.disc_fraction(np.array([-1.0, -0.27, 0.0, 0.27, 1.0]), 0.27)
    assert f == pytest.approx([0, 0, 0.5, 1, 1], abs=1e-12)
    assert np.all(np.diff(visibility.disc_fraction(np.linspace(-0.3, 0.3, 50), 0.27)) >= 0)


def test_disc_fraction_matches_monte_carlo():
    rng = np.random.default_rng(1)
    p = rng.uniform(-1, 1, (200000, 2))
    p = p[(p ** 2).sum(1) <= 1]
    for c in (-0.6, -0.2, 0.3, 0.8):  # centre c radii above the line y = -c
        assert visibility.disc_fraction(c, 1.0) == pytest.approx(np.mean(p[:, 1] >= -c), abs=0.005)


def test_horizon_at_is_periodic_and_2d_matches_1d():
    h = np.sin(np.radians(AZ)) * 3
    assert visibility.horizon_at(AZ, h, 359.75) == pytest.approx((h[-1] + h[0]) / 2)
    assert visibility.horizon_at(AZ, h, -90) == pytest.approx(-3)
    h2 = np.stack([h, 2 * h])
    q = np.array([10.2, 359.9, 181.0])
    np.testing.assert_allclose(visibility.horizon_at(AZ, h2, q)[1], visibility.horizon_at(AZ, 2 * h, q), atol=1e-12)


def test_horizon_sigma():
    assert visibility.horizon_sigma_deg(1000.0, 1.0) == pytest.approx(np.degrees(np.arctan(1e-3)))


# --- eclipse ---

def test_overlap_fraction_cases():
    assert eclipse.overlap_fraction(0.27, 0.95, 0.0) == 1.0
    assert eclipse.overlap_fraction(0.27, 0.95, 1.3) == 0.0
    assert eclipse.overlap_fraction(1.0, 0.5, 0.0) == pytest.approx(0.25)
    # equal circles at separation r: lens area = (2pi/3 - sqrt(3)/2) r^2
    assert eclipse.overlap_fraction(1.0, 1.0, 1.0) == pytest.approx((2 * np.pi / 3 - np.sqrt(3) / 2) / np.pi)
    f = eclipse.overlap_fraction(0.27, 0.95, np.linspace(0, 1.3, 100))
    assert np.all(np.diff(f) <= 1e-12)


def test_angular_separation():
    assert eclipse.angular_separation(0, 0, 90, 0) == pytest.approx(90)
    assert eclipse.angular_separation(10, 89, 190, 89) == pytest.approx(2, abs=1e-9)


def test_effective_sun():
    assert eclipse.effective_sun(0.5, 0.5) == 0.25


def test_real_eclipse_seen_from_im2_on_2025_03_14():
    """Total lunar eclipse of 14 Mar 2025 = Earth covering the Sun from the Moon (Blue Ghost 1 filmed it)."""
    tl = engine.timeline(engine.load_site("im2_actual"), "2025-03-13", 3, 2.0)
    assert tl["eclipse"].max() == pytest.approx(1.0)
    peak = tl.loc[tl["eclipse"].idxmax(), "utc"]
    assert pd.Timestamp("2025-03-14 04:00Z") <= peak <= pd.Timestamp("2025-03-14 09:00Z")


# --- events ---

T = pd.date_range("2027-01-01", periods=240, freq="1h", tz="UTC")


def test_crossings_of_a_sine_wave():
    hours = np.arange(len(T))
    v = np.sin(2 * np.pi * hours / 48.0 + 0.3)
    c = events.crossings(T, v)
    rises = c.loc[c["kind"] == "rise", "utc"]
    exact = T[0] + pd.to_timedelta((48.0 - 0.3 * 48 / (2 * np.pi)) % 48, unit="h")
    assert abs((rises.iloc[0] - exact).total_seconds()) < 600  # linear interpolation of an hourly sine
    assert (c["kind"].iloc[::2] != c["kind"].iloc[1::2].to_numpy()).all()


def test_windows_and_longest_with_microsecond_timestamps():
    t = T.as_unit("us")
    m = np.zeros(len(t), bool)
    m[10:20] = True
    m[50:80] = True
    w = events.windows(t, m)
    assert list(w["duration_h"]) == [10, 30]
    assert events.longest(t, m)["hours"] == 30
    assert events.windows(t, np.zeros(len(t), bool)).empty
    assert events.longest(t, np.zeros(len(t), bool))["hours"] == 0


def test_countdown_with_uncertainty():
    hours = np.arange(len(T))
    v = 0.5 - hours * 0.01  # sets at hour 50
    cd = events.countdown(T, v, T[0], "set", sigma=0.1)
    assert cd["hours"] == pytest.approx(50, abs=0.01)
    assert cd["earliest"] < cd["utc"] < cd["latest"]
    assert (cd["latest"] - cd["earliest"]).total_seconds() / 3600 == pytest.approx(20, abs=0.1)
    assert events.format_hours(50) == "2 d 2 h" and events.format_hours(0.5) == "30 min"


# --- comms ---

def test_bands_and_link():
    b = comms.band(np.array([-1, 0.5, 2.0, 4.9, 5.0, 12]))
    assert list(b) == ["none", "poor", "marginal", "marginal", "good", "good"]
    assert list(comms.band(np.array([3.0]), {"good": 3.0})) == ["good"]
    assert list(comms.band_rank(b)) == [0, 1, 2, 2, 3, 3]
    assert list(comms.link_usable(b, [True, True, True, False, True, True])) == [0, 0, 1, 0, 1, 1]


def test_dsn_moon_elevation_is_plausible():
    t = pd.date_range("2027-03-01", periods=48, freq="1h", tz="UTC")
    el = comms.dsn_moon_elevation(t)
    assert list(el.columns) == ["Goldstone", "Madrid", "Canberra"]
    assert el.abs().max().max() <= 90
    for col in el:  # the Moon rises and sets once a day at every complex
        assert (el[col] > 0).any() and (el[col] < 0).any()
    assert comms.dsn_in_view(t)["any"].mean() > 0.6


# --- power ---

def test_array_power_geometry():
    assert power.array_power(0.0, 1.0, 100, "vertical") == pytest.approx(100)
    assert power.array_power(0.0, 1.0, 100, "horizontal") == pytest.approx(0)
    assert power.array_power(30.0, 0.5, 100, "horizontal") == pytest.approx(25)


@pytest.mark.parametrize("unit", ["s", "us", "ns"])
def test_battery_drains_by_the_hour_whatever_the_time_unit(unit):
    t = T[:12].as_unit(unit)
    b = power.battery(t, np.zeros(12), load_W=100, capacity_Wh=1000)
    assert b["soc"][:3] == pytest.approx([1.0, 0.9, 0.8])
    assert not b["survives"] and b["first_below"] == t[9]  # 0.1 left after 9 h
    many = power.battery(t, np.zeros((3, 12)), load_W=10, capacity_Wh=1000)
    assert many["survives"].all() and many["soc"].shape == (3, 12)


# --- landing ---

def _tile(h_deg, slope=2.0, n=10):
    return {"az": AZ, "h_el": np.full((n, 720), h_deg, np.float32), "x": np.zeros(n), "y": np.zeros(n),
            "lat": np.full(n, -85.0), "lon": np.zeros(n), "slope_deg": np.full(n, slope), "psr_dist_m": np.ones(n)}


def test_landing_light_shadow_and_camera():
    lit = landing.landing_light(_tile(0.0), sun_az=90, sun_el=3.0, approach_heading=180)
    assert lit["shadow_pct"] == 0 and not lit["sun_in_camera"] and lit["rating"] == "good"
    assert lit["boulder_shadow_m"] == pytest.approx(1 / np.tan(np.radians(3)))
    dark = landing.landing_light(_tile(5.0), sun_az=90, sun_el=3.0)
    assert dark["shadow_pct"] == 100 and dark["rating"] == "bad"
    glare = landing.landing_light(_tile(0.0), sun_az=170, sun_el=3.0, approach_heading=180)
    assert glare["sun_in_camera"] and glare["rating"] == "caution"
    half = _tile(0.0)
    half["h_el"][:5] = 10
    assert landing.landing_light(half, 90, 3.0)["shadow_pct"] == 50


def _flat_timeline(days=5, sun_el=3.0, earth_el=8.0):
    t = pd.date_range("2027-01-01", periods=24 * days, freq="1h", tz="UTC")
    tl = pd.DataFrame({"utc": t, "sun_az": np.linspace(0, 360 * days / 29.5, len(t)) % 360, "sun_el": sun_el,
                       "earth_az": 0.0, "earth_el": earth_el, "sun_r": 0.27, "earth_r": 0.95, "eclipse": 0.0,
                       "dsn": True})
    return tl


def test_ellipse_odds_slope_and_light():
    lander = {"array_W": 300, "panel": "vertical", "load_W": 100, "battery_Wh": 1000}
    tile = _tile(0.0)
    tile["slope_deg"][:3] = 15.0
    o = landing.ellipse_odds(tile, _flat_timeline(), lander)
    assert o["rates"]["slope"] == pytest.approx(0.7) and o["rates"]["power"] == 1.0
    assert o["p_success"] == pytest.approx(0.7)
    blocked = landing.ellipse_odds(_tile(6.0), _flat_timeline(), lander)
    assert blocked["rates"]["light"] == 0 and blocked["rates"]["power"] == 0 and blocked["p_success"] == 0
    assert blocked["rates"]["comms"] == 1.0  # Earth at 8 deg still clears a 6 deg horizon by 2 deg


def test_max_slope_is_nasas_landing_requirement():
    assert landing.MAX_SLOPE_DEG == 10.0


# --- scores on real sites ---

def test_summary_names_the_occluder():
    site = engine.load_site("blue_moon_mk1_target")  # ridge: distant horizon is Shackleton / Henson
    j = site.mast_row(2.0)
    k = next(k for k in range(720) if site.occ_name[j, k] and site.dist[j, k] > 2000 and site.horizon(2.0)[k] > 0.1)
    line = scores.blame_at(site, 2.0, "sun", float(site.az[k]), 0.0, pd.Timestamp("2027-03-04T05:00Z"))
    assert str(site.occ_name[j, k]) in line and "km away" in line and line.endswith("from 4 Mar 05:00 UTC")


def test_summary_fields_and_reasons():
    site = engine.load_site("im2_actual")
    tl = engine.timeline(site, "2025-03-06T17:00Z", 7, 2.0)  # ends before the 14 Mar eclipse
    s = scores.summary(site, tl)
    assert 0 <= s["pct_both"] <= s["pct_sunlit"] <= 100
    assert s["eclipses"] == 0 and s["survives"]
    assert any(r.startswith("Sunlit") for r in s["reasons"])
    longer = scores.summary(site, engine.timeline(site, "2025-03-06T17:00Z", 14, 2.0))
    assert longer["eclipses"] == 1 and any("eclipses the Sun" in r for r in longer["reasons"])
    assert scores.verdict(s)["power"] in ("good", "caution", "bad")


def test_custom_site_runs_on_the_coarse_dem():
    c = engine.custom_site(-89.45, -137.3)
    assert c.custom and c.horizon_source == "dem_80s_160m" and c.el.shape == (6, 720)
    assert np.all(np.diff(c.el, axis=0) <= 1e-6)
    with pytest.raises(ValueError):
        engine.custom_site(-70.0, 0.0)


def test_ephemeris_falls_back_to_spice_outside_the_tables():
    site = engine.load_site("im2_actual")
    pre = engine.ephemeris(site, "2027-01-01T00:00Z", "2027-01-01T03:00Z")
    rt = engine.sun_earth_azel(site.lat, site.lon, pre["utc"])
    np.testing.assert_allclose(pre["sun_el"], rt["sun_el"], atol=1e-4)
    out = engine.ephemeris(site, "2030-01-01T00:00Z", "2030-01-01T03:00Z")
    assert len(out) == 3 and out["sun_el"].notna().all()


def test_mast_interpolation():
    site = engine.load_site("change_7_target")
    np.testing.assert_allclose(site.horizon(2.0), site.el[1])
    mid = site.horizon(3.5)
    assert np.all(mid <= site.el[1] + 1e-9) and np.all(mid >= site.el[2] - 1e-9)


def test_countdowns_have_uncertainty_windows():
    site = engine.load_site("blue_moon_mk1_target")
    tl = engine.timeline(site, "2027-01-01T00:00Z", 30, 2.0)
    cd = scores.countdowns(site, tl)
    assert set(cd) >= {"sunset", "sunrise", "earthset", "earthrise", "sigma_z_m"}
    assert 0.1 <= cd["sigma_z_m"] < 20
    for k in ("sunset", "sunrise", "earthset", "earthrise"):
        c = cd[k]
        if pd.notna(c["utc"]):
            assert c["earliest"] <= c["utc"] <= c["latest"] and c["hours"] >= 0
