# Lunar Landing Site Navigator

NASA Space Apps 2026 entry. Deadline: **Sun 15 Nov 2026, 23:59 IST**.
Goal: the **least custom code possible**. We stitch together open-source libraries and NASA data and write only glue.

- Feature plan and competitive analysis: `docs/plan/` (Tier A = must have, Tier B = differentiators, Tier C = polish). Local only: gitignored so it stays out of the public repo.
- Phase prompts 0–9 and the ATTRIBUTIONS template: build kit doc, https://claude.ai/artifact/Y6hRKTp9fUpTvh7hdQ11dh

## Rules

1. **Prefer an existing library over new code.** Before writing any function over ~30 lines, check whether SpiceyPy, NumPy, SciPy, pandas, rasterio/rioxarray, pyproj, Shapely/GeoPandas, Skyfield, astroquery, Plotly or Streamlit already does it.
2. **Allowed licenses: MIT, BSD, Apache-2.0, ISC, NASA public data.** Never add GPL, AGPL or LGPL code or dependencies.
   Scope: this covers code we write or vendor and every Python package we list. Some permissive packages dynamically link copyleft native libraries that conda/pip install for the user (e.g. GEOS, LGPL-2.1, under Shapely/GeoPandas). We never modify or redistribute those; they are listed under "Transitive native libraries" in `ATTRIBUTIONS.md`. Before adding a package, check its license and its new native libraries (`conda-meta/*.json` has a `license` field).
3. **Every library, dataset, vendored file and borrowed idea gets a line in `ATTRIBUTIONS.md`** (name, URL, license, what we use it for) in the same commit that introduces it. `tests/test_repo.py` checks that every package in `requirements.txt` is listed.
4. **Vendored code lives in `vendor/`** with its original LICENSE file (and NOTICE, if any) and a header in each file naming the source and our changes.
5. **Heavy computation runs offline in `pipeline/`** and writes compact files to `data/derived/` (npz, parquet, json). **The app makes no network calls at runtime.**
6. **Times in UTC. Frame `MOON_ME`. Angles in degrees. Azimuth is compass: 0 = local north (direction of increasing latitude), 90 = east.**
7. **Keep `docs/METHOD.md` (method + known limits) updated as you go**, in the same change as the code it describes.
8. **Logic lives in `navigator/` as pure, tested functions; `app/` only does UI.**

## Conventions (detail for rule 6)

- Latitude planetocentric, longitude east-positive, both in degrees; longitude in [-180, 180).
- Lunar reference sphere: radius 1737.4 km (the LOLA DEMs use it). Heights in metres in DEMs, in km inside SPICE calls.
- Sun/Earth topocentric az/el: `spiceypy.azlcpo(method="ELLIPSOID", ..., abcorr="LT+S", azccw=False, elplsz=True, obsctr="MOON", obsref="MOON_ME")`. Do not hand-roll topocentric maths.
- Timestamps: timezone-aware UTC in pandas (`utc=True`); ISO strings end in `Z`.
- Read map projections from the data files' CRS (south polar stereographic). Never hardcode one.

## Layout

```
pipeline/    offline only: fetch_data.py, ephem.py, horizon.py, sites.py, sites.yaml, landers.yaml, build_all.py
navigator/   pure, tested logic: geo, engine, visibility, eclipse, events, comms, power, scores, landing, replan, plots
app/         Streamlit UI only: Home.py + pages/
vendor/      third-party code, unmodified except where its header says
data/raw/    downloads (gitignored)
data/derived/ committed outputs; every file < 50 MB (enforced by tests/test_repo.py)
tests/       pytest
docs/        METHOD.md (method + known limits), plan/ (feature plan)
```

## Commands

```
make env       # create the conda env "lunar-nav" (Python 3.11, GDAL from conda-forge)
make data      # pipeline/fetch_data.py -> data/raw/
make derived   # pipeline/build_all.py  -> data/derived/
make test      # pytest
make app       # streamlit run app/Home.py
```

## Working notes

- Work one phase (build kit prompt) at a time. Each phase ends with `make test` passing, then a commit `Phase N: <what>` and a push to GitHub (`origin main`).
- Two dependency sets, same pins:
  - `requirements.txt` = the deployed app only: streamlit, plotly, numpy, pandas, pyarrow, scipy, spiceypy, skyfield, rasterio, pyproj, pyyaml.
  - `pipeline/environment.yml` = everything (app + pipeline + tests), including GDAL, GeoPandas, Shapely, astroquery, Numba, joblib. It stays in `pipeline/`, never the repo root: Streamlit Community Cloud prefers a root `environment.yml` over `requirements.txt`.
  - A new app dependency goes in both files; a pipeline-only one goes in `pipeline/environment.yml` only. Either way, add it to `ATTRIBUTIONS.md` in the same change.
- **`app/` and `navigator/` never import `osgeo`, `geopandas`, `shapely`** (or other pipeline-only packages). `tests/test_repo.py` enforces it. Whatever needs them is precomputed by the pipeline, e.g. PSR distances per site and per ellipse point, and `data/derived/psr_outlines.geojson` (simplified, < 5 MB, drawn with Plotly).
- Custom lat/lon sites compute their horizon at runtime from `data/derived/dem_80s_160m.tif` (LDEM_80S_80MPP_ADJ averaged to 160 m). The vendored MMGIS HorizonProfile.py runs there on `navigator.geo.gdal_compat` / `osr_compat` (rasterio + pyproj stand-ins), not on GDAL. The UI labels these sites "coarser terrain (160 m) than catalog sites".
- No static image export library: PNGs come from Plotly's built-in download button, and the decision brief embeds charts as HTML.
- Tests that need the network are marked `@pytest.mark.network` and are skipped by `make test`. Run them with `pytest -m network`.
- Competitor repos are for ideas only: credit them under "Ideas and inspiration" in `ATTRIBUTIONS.md` and never copy their app code (the Space Apps "original work" checkbox).
- Label every number we did not source as illustrative (lander presets, region centres, comm thresholds).
