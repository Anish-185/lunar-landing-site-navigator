# Lunar Landing Site Navigator

NASA Space Apps 2026. A planning tool that shows when a lunar landing site has sunlight and a line of sight to Earth, explains why (which ridge blocks the Sun), and re-plans when a launch slips.

**Status:** Phase 3, terrain horizons with named occluders, landing ellipses, PSR distances, validation against NASA's illumination maps. No app features yet. The method and its limits are in [`docs/METHOD.md`](docs/METHOD.md).

## Setup

Needs conda (Miniforge recommended). GDAL's Python bindings come from conda-forge.

```bash
make env                 # creates the "lunar-nav" env (Python 3.11)
conda activate lunar-nav
make test
```

`pipeline/environment.yml` is the full environment for the offline pipeline and the tests. `requirements.txt` is only what the deployed app needs (pip, no GDAL, GeoPandas or Shapely).

## Commands

| Command | What it does |
| --- | --- |
| `make data` | Download NASA data into `data/raw/` (gitignored) |
| `make derived` | Precompute ephemerides, horizons and tiles into `data/derived/` (committed) |
| `make test` | Run the tests |
| `make app` | Start the Streamlit app (no network calls at runtime) |

## Layout

- `pipeline/`: offline data download and precomputation
- `navigator/`: pure, tested logic
- `app/`: Streamlit UI
- `vendor/`: third-party code with its original licenses
- `data/derived/`: compact precomputed outputs
- `docs/`: method and known limits

## Credits and license

Every library, dataset, vendored file and borrowed idea is listed in [`ATTRIBUTIONS.md`](ATTRIBUTIONS.md). Code is written with Claude Code (Anthropic); the team reviews and tests it and is responsible for it.

Licensed under Apache-2.0 ([`LICENSE`](LICENSE)).
