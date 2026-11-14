"""Build everything in data/derived/ from data/raw/ (`make derived`).

Phase 1: the 160 m DEM for custom sites. Phase 4 adds ephemeris, horizons and tiles for every
catalog site in parallel (joblib).
"""

from pipeline import horizon


def main() -> None:
    dem = horizon.build_coarse_dem()
    print(f"{dem.relative_to(horizon.ROOT)}: {dem.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
