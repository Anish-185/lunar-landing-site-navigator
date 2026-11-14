"""Build everything in data/derived/ from data/raw/ (`make derived`).

Phase 1: the 160 m DEM for custom sites. Phase 2: kernels for the app, hourly ephemeris for every catalog site,
and residuals against the cached JPL Horizons responses. Phase 3 adds horizons and landing-ellipse tiles.
"""

from pipeline import ephem, horizon


def main() -> None:
    dem = horizon.build_coarse_dem()
    print(f"{dem.relative_to(horizon.ROOT)}: {dem.stat().st_size / 1e6:.1f} MB")
    seconds = ephem.build_all()
    print(f"ephemeris: {len(list(ephem.EPHEM_DIR.glob('*.parquet')))} sites in {seconds:.1f} s")
    res = ephem.write_validation()
    print(f"Horizons validation: max separation {res['sep'].max():.2e} deg over {len(res)} comparisons")


if __name__ == "__main__":
    main()
