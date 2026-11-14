"""Build everything in data/derived/ from data/raw/ (`make derived`).

Phase 1: the 160 m DEM for custom sites. Phase 2: kernels for the app, hourly ephemeris for every catalog site and
residuals against cached JPL Horizons responses. Phase 3: feature names, terrain horizons with occluders,
landing-ellipse tiles (~30 min), PSR distances and outlines, and the AVGVISIB validation.
"""

import time

from pipeline import ephem, horizon


def _step(label, fn):
    t0 = time.time()
    result = fn()
    print(f"{label}: {time.time() - t0:.1f} s", flush=True)
    return result


def main() -> None:
    _step("160 m DEM", horizon.build_coarse_dem)
    _step("ephemeris (17 sites, hourly)", ephem.build_all)
    res = _step("Horizons validation", ephem.write_validation)
    print(f"  max separation {res['sep'].max():.2e} deg over {len(res)} comparisons")
    _step("USGS feature names", horizon.build_features)
    _step("site horizons (17 sites x 6 masts)", horizon.build_site_horizons)
    _step("PSR outlines", horizon.build_psr_outlines)
    _step("site PSR distances", horizon.site_psr_table)
    _step("landing-ellipse tiles (14 sites x 200 points)", horizon.build_tiles)
    av = _step("AVGVISIB validation", horizon.validate_avgvisib)
    print(f"  sites over 10 points: {list(av.loc[av['flag_over_10pct'], 'site_id'])}")


if __name__ == "__main__":
    main()
