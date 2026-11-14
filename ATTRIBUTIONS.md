# Attributions

Every external resource used in this project, as the NASA Space Apps terms require. A row is added in the same commit that introduces the resource (CLAUDE.md rule 3).

## NASA and space-agency data

| Resource | Provider | License | Use | Link |
|---|---|---|---|---|
| LOLA south polar DEM 80 m (`LDEM_80S_80MPP_ADJ.TIF`), slope (`LDSM_80S_80MPP_ADJ.TIF`), height error (`LDEM_80S_80MPP_ADJ_ERR.TIF`), PSRs > 1 km² (`LPSR_80S_20MPP_ADJ_1km2` shapefile); PGDA product 90 | NASA GSFC / LOLA team. Cite: Barker et al. (2023), Planet. Sci. J. 4, 183, doi:10.3847/PSJ/acf3e1; data doi:10.60903/gsfcpgda-lola-spole | NASA public data | Far-field horizons, slope, height uncertainty, PSR distance; source of `data/derived/dem_80s_160m.tif` (2×2 block average, int16) | https://pgda.gsfc.nasa.gov/products/90 |
| LOLA south polar DEM and slope 20 m (`LDEM_80S_20MPP_ADJ.TIF`, `LDSM_80S_20MPP_ADJ.TIF`); PGDA product 90 | as above | NASA public data | Near-field horizons and landing-zone slope; read remotely in windows (`/vsicurl/`), not stored | https://pgda.gsfc.nasa.gov/products/90 |
| LOLA average Sun and Earth visibility maps (`AVGVISIB_85S_060M_201608[_EARTH].TIF`, `AVGVISIB_75S_120M_201608[_EARTH].TIF`); PGDA product 69 | NASA GSFC. Cite: Mazarico et al. (2011), Icarus 211, 1066–1081, doi:10.1016/j.icarus.2010.10.030 | NASA public data | Map layer; validation of our long-run sunlit and Earth-visible fractions | https://pgda.gsfc.nasa.gov/products/69 |
| NAIF SPICE generic kernels: `naif0012.tls`, `pck00011.tpc`, `de440s.bsp`, `moon_pa_de440_200625.bpc`, `moon_de440_250416.tf` | NASA JPL NAIF | NASA public data | Sun/Earth ephemeris (DE440), lunar orientation and the `MOON_ME` frame | https://naif.jpl.nasa.gov/pub/naif/generic_kernels/ |

## Open-source libraries

### Deployed app (`requirements.txt`)

| Library | License | Use | Link |
|---|---|---|---|
| Streamlit | Apache-2.0 | Web app | https://github.com/streamlit/streamlit |
| Plotly (plotly.py) | MIT | Every chart; PNG via its built-in download button | https://github.com/plotly/plotly.py |
| NumPy | BSD-3-Clause | Arrays and numerics | https://numpy.org |
| pandas | BSD-3-Clause | Time series tables | https://pandas.pydata.org |
| PyArrow | Apache-2.0 | Parquet files in `data/derived/` | https://arrow.apache.org/docs/python/ |
| SciPy | BSD-3-Clause | Interpolation, statistics | https://scipy.org |
| SpiceyPy (wraps NAIF CSPICE) | MIT (CSPICE: NAIF, free public release) | Sun/Earth ephemeris on the lunar surface | https://github.com/AndrewAnnex/SpiceyPy |
| Skyfield | MIT | DSN station visibility of the Moon | https://rhodesmill.org/skyfield/ |
| rasterio | BSD-3-Clause | DEM reads and windows; backs the GDAL stand-in in `navigator/geo.py` | https://github.com/rasterio/rasterio |
| pyproj (wraps PROJ, MIT) | MIT | Polar stereographic projection; backs the OSR stand-in in `navigator/geo.py` | https://github.com/pyproj4/pyproj |
| PyYAML | MIT | Site and lander catalogs | https://github.com/yaml/pyyaml |

### Offline pipeline and tests only (`environment.yml`, on top of the above)

| Library | License | Use | Link |
|---|---|---|---|
| GDAL (Python bindings, conda-forge) | MIT | Needed by the vendored NASA MMGIS Sightline scripts | https://gdal.org |
| GeoPandas | BSD-3-Clause | PSR shapefile, distance to PSR, simplified PSR outlines | https://geopandas.org |
| Shapely | BSD-3-Clause | PSR polygon geometry | https://github.com/shapely/shapely |
| astroquery | BSD-3-Clause | JPL Horizons validation | https://astroquery.readthedocs.io |
| Numba | BSD-2-Clause | Fast loops in the pipeline | https://numba.pydata.org |
| joblib | BSD-3-Clause | Parallel precomputation | https://joblib.readthedocs.io |
| rioxarray | Apache-2.0 | Raster I/O into xarray | https://github.com/corteva/rioxarray |
| xarray | Apache-2.0 | Labelled raster arrays | https://xarray.dev |
| pytest | MIT | Tests | https://pytest.org |

### Transitive native libraries with copyleft or non-standard licenses

Pulled in by the pipeline packages above (mostly GDAL, GeoPandas, Shapely) and installed by conda; we do not modify or redistribute them. From a license audit of the `lunar-nav` conda env on 2026-11-14 (289 packages); everything else in it is permissive.

| Library | License | Pulled in by |
|---|---|---|
| GEOS | LGPL-2.1 | Shapely, GeoPandas, GDAL |
| librttopo | GPL-2.0-or-later | libspatialite, inside conda-forge libgdal-core (GDAL) |
| libspatialite, freexl | MPL-1.1 | libgdal-core (GDAL) |
| lzo | GPL-2.0-or-later | libarchive, inside libgdal-core (GDAL) |
| libiconv | LGPL-2.1 | libgdal-core, libxml2 |
| readline | GPL-3.0 | the conda-forge Python interpreter and sqlite |
| cairo, fribidi, graphite2, libglib | LGPL / MPL-1.1 | Matplotlib (required by GeoPandas) text rendering |
| freetype | FTL or GPL-2.0 (dual; we use it under FTL) | Matplotlib |
| certifi | MPL-2.0 | requests (Streamlit, astroquery) |
| GCC runtime (libgcc, libstdc++, libgfortran, libgomp) | GPL-3.0 with GCC Runtime Library Exception | compiled packages (NumPy, SciPy, ...) |
| Qhull | Qhull license (permissive) | Matplotlib |

## Vendored code (modified)

| Code | Source | License | Our changes |
|---|---|---|---|
| *(added in Phase 3)* | | | |

## Ideas and inspiration (no code copied)

| Project | Link | What inspired us |
|---|---|---|
| *(added when a feature draws on it)* | | |

## Research and mission references

- NASA, Artemis HLS overview for Space Apps 2025 (landing criteria): https://ntrs.nasa.gov/api/citations/20250009323/downloads/ArtemisOverview2025IntSPAPPSChallenge.pdf
- Other references are listed in `docs/plan/competitive-analysis.md` and added here as features use them.

## AI assistance

Code is written with Claude Code (Anthropic) from prompts by the team; the team reviews and tests it and is responsible for all of it.
