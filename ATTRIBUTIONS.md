# Attributions

Every external resource used in this project, as the NASA Space Apps terms require. A row is added in the same commit that introduces the resource (CLAUDE.md rule 3).

## NASA and space-agency data

| Resource | Provider | License | Use | Link |
|---|---|---|---|---|
| LOLA south polar DEM 80 m (`LDEM_80S_80MPP_ADJ.TIF`), slope (`LDSM_80S_80MPP_ADJ.TIF`), height error (`LDEM_80S_80MPP_ADJ_ERR.TIF`), PSRs > 1 km² (`LPSR_80S_20MPP_ADJ_1km2` shapefile); PGDA product 90 | NASA GSFC / LOLA team. Cite: Barker et al. (2023), Planet. Sci. J. 4, 183, doi:10.3847/PSJ/acf3e1; data doi:10.60903/gsfcpgda-lola-spole | NASA public data | Far-field horizons, slope, height uncertainty, PSR distance; source of `data/derived/dem_80s_160m.tif` (2×2 block average, int16) | https://pgda.gsfc.nasa.gov/products/90 |
| LOLA south polar DEM and slope 20 m (`LDEM_80S_20MPP_ADJ.TIF`, `LDSM_80S_20MPP_ADJ.TIF`); PGDA product 90 | as above | NASA public data | Near-field horizons and landing-zone slope; read remotely in windows (`/vsicurl/`), not stored | https://pgda.gsfc.nasa.gov/products/90 |
| LOLA average Sun and Earth visibility maps (`AVGVISIB_85S_060M_201608[_EARTH].TIF`, `AVGVISIB_75S_120M_201608[_EARTH].TIF`); PGDA product 69 | NASA GSFC. Cite: Mazarico et al. (2011), Icarus 211, 1066–1081, doi:10.1016/j.icarus.2010.10.030 | NASA public data | Map layer; validation of our long-run sunlit and Earth-visible fractions | https://pgda.gsfc.nasa.gov/products/69 |
| NAIF SPICE generic kernels: `naif0012.tls`, `pck00011.tpc`, `de440s.bsp`, `moon_pa_de440_200625.bpc`, `moon_de440_250416.tf` | NASA JPL NAIF | NASA public data | Sun/Earth ephemeris (DE440), lunar orientation and the `MOON_ME` frame | https://naif.jpl.nasa.gov/pub/naif/generic_kernels/ |
| LOLA DEM 240 m, 60°S–90°S (`LDEM_60S_240MPP_ADJ.TIF`); PGDA product 90 | as above | NASA public data | Terrain horizon for Chandrayaan-3 (one 205 km window read remotely and cached, not stored) | https://pgda.gsfc.nasa.gov/products/90 |
| USGS Gazetteer of Planetary Nomenclature, Moon feature centre points (`MOON_nomenclature_center_pts.zip`) | USGS Astrogeology / IAU WGPSN | Public domain (U.S. Government) | Names, centres and diameters of craters and montes for naming the terrain that blocks the Sun or Earth; reduced to `data/derived/lunar_features.csv` | https://planetarynames.wr.usgs.gov/ |
| AVGVISIB PDS labels and illumination README (LOLA PDS node) | NASA GSFC / MIT | NASA public data | Definition of the AVGVISIB values (any part of the disc visible) for our validation | http://imbrium.mit.edu/EXTRAS/ILLUMINATION/ |
| JPL Horizons (apparent Sun and Earth AZ/EL for observers on the Moon) | NASA JPL Solar System Dynamics | NASA public service | Validation reference for our ephemeris; responses cached in `tests/fixtures/horizons.csv` | https://ssd.jpl.nasa.gov/horizons/ |
| LRO Diviner Polar Resource Product, south (`DLRE_PRP_SOUTH.TAB`, PDS data set LRO-L-DLRE-5-PRP-V2.0, doi:10.17189/1520650; PDS4 bundle `lro_diviner_derived1`) | NASA / UCLA Diviner team (D. A. Paige). Cite: Paige et al. (2010), Science 330, 479–482, doi:10.1126/science.1187726 | NASA public data | Phase 9 thermal layer: annual max/average surface temperature and ice depth, gridded to 1 km (`data/derived/thermal_south.npz`) and averaged within 500 m of each site (`data/derived/site_thermal.csv`); cold traps < 110 K | https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/ |
| DSN complex positions (Goldstone, Madrid, Canberra) | NASA JPL Deep Space Network | NASA public data | Moon elevation at each complex (`navigator/comms.py`) | https://www.nasa.gov/directorates/somd/space-communications-navigation-program/deep-space-network/ |

## Images and textures (NASA public-domain media; fetched and compressed by `pipeline/media.py`)

| Resource | Credit | License | Use | Link |
|---|---|---|---|---|
| Hubble, "Mystic Mountain" in the Carina Nebula (NASA image GSFC_20171208_Archive_e002076) | NASA, ESA, and M. Livio and the Hubble 20th Anniversary Team (STScI) | Public domain (NASA / STScI, no copyright asserted) | Darkened app background (`app/static/nebula.webp`) and story-site nebula layer | https://images.nasa.gov/details/GSFC_20171208_Archive_e002076 |
| CGI Moon Kit: LROC colour mosaic with poles (`lroc_color_poles_2k.tif`) and LOLA elevation (`ldem_3_8bit.jpg`), NASA SVS 4720 | NASA's Scientific Visualization Studio; LRO LROC and LOLA teams | NASA public domain | 3D Moon texture and bump map on the story site | https://svs.gsfc.nasa.gov/4720 |
| Blue Marble (`bluemarble-2048.png`), NASA SVS 2915 | NASA Goddard Space Flight Center / SVS (Blue Marble: Reto Stöckli, NASA Earth Observatory) | NASA public domain | 3D Earth texture on the story site | https://svs.gsfc.nasa.gov/2915 |
| South-pole hillshade (`site/public/media/pole_hillshade.webp`) | Ours, computed from the LOLA 80 m DEM (PGDA 90, above) at an 8° Sun | Derived from NASA public data | Parallax terrain layers on the story site | `pipeline/media.py` |

## Fonts and icons

| Resource | License | Use | Link |
|---|---|---|---|
| Instrument Serif, via Fontsource `@fontsource/instrument-serif` | SIL Open Font License 1.1 (`app/static/fonts/LICENSE-InstrumentSerif-OFL.txt`) | Display headings, app and story site | https://github.com/Instrument/instrument-serif |
| Geist (variable), via Fontsource `@fontsource-variable/geist` | SIL Open Font License 1.1 (`app/static/fonts/LICENSE-Geist-OFL.txt`) | Body text, UI and large figures | https://github.com/vercel/geist-font |
| Geist Mono (variable), via Fontsource `@fontsource-variable/geist-mono` | SIL Open Font License 1.1 (`app/static/fonts/LICENSE-GeistMono-OFL.txt`) | Readouts: times, angles, chart ticks | https://github.com/vercel/geist-font |
| Lucide icons (`lucide`, `lucide-static`) | ISC (`app/static/icons/LICENSE-lucide-ISC.txt`) | Status and card icons | https://lucide.dev |

## Site catalog sources (`pipeline/sites.yaml`, `pipeline/landers.yaml`)

| Source | What we took | Link |
|---|---|---|
| NASA release 24-136, "NASA Provides Update on Artemis III Moon Landing Regions" (28 Oct 2024), region map (NASA/GSFC/ASU/JSC/AGDT) | The nine region names; region centres measured from the map | https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/ |
| LROC (NASA/GSFC/Arizona State University), images 1401, 1408, 1360, 1400 | IM-2 target and resting spot; IM-1 position and touchdown time; Blue Ghost 1 landing region | https://lroc.im-ldi.com/images/1401, https://lroc.im-ldi.com/images/1408, https://lroc.im-ldi.com/images/1360, https://www.lroc.im-ldi.com/images/1400 |
| NSSDC, Apollo landing site coordinates (Wagner et al. 2017, Icarus 283) | Apollo 11 Lunar Module position | https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html |
| Gracy & Lee (2024), LPSC 55, abstract 1695 | Connecting Ridge site used for Blue Moon MK1 | https://www.hou.usra.edu/meetings/lpsc2024/pdf/1695.pdf |
| arXiv 2406.19863, "Evaluating potential landing sites for the Artemis III mission using a multi-criteria decision making approach" | Cross-check points for Nobile Rim 2 and de Gerlache Rim 2 | https://arxiv.org/abs/2406.19863 |
| Wikipedia (CC BY-SA; facts only, no text copied): Statio Shiv Shakti, Chang'e 7, IM-1, IM-2, Blue Ghost Mission 1, Chandrayaan-3 | Chandrayaan-3 and Chang'e-7 coordinates; launch and landing times; Vikram lander power | https://en.wikipedia.org/wiki/Statio_Shiv_Shakti and the other article titles |
| NASA, Blue Moon MK1 CLPS flight page | MK1 targets the Shackleton Connecting Ridge | https://www.nasa.gov/event/clps-flight-blue-origins-blue-moon-mark-1/ |

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

### Story site (`site/package.json`, built with Vite to static files)

| Library | License | Use | Link |
|---|---|---|---|
| three.js | MIT | 3D Moon and Earth (lit from the SPICE Sun direction), Big Bang particle opening, the "be the Sun" relit polar terrain shader | https://threejs.org |
| Lenis | MIT | Smooth scrolling | https://github.com/darkroomengineering/lenis |
| Motion (motion.dev) | MIT | Scroll-linked reveals and parallax (instead of GSAP, whose license is not OSI open source) | https://motion.dev |
| Plotly.js (`plotly.js-dist-min`) | MIT | Story charts | https://github.com/plotly/plotly.js |
| Fontsource (font packaging) | MIT (fonts themselves OFL) | Self-hosted fonts | https://fontsource.org |
| Vite | MIT | Build tool (dev only) | https://vite.dev |
| Playwright | Apache-2.0 | Screenshots of the app and story site; demo frame capture and the deck PDF (`site/scripts_demo_*.mjs`, dev only) | https://playwright.dev |
| FFmpeg (system command-line tool, not a dependency; not distributed) | LGPL-2.1+/GPL-2.0+ (as built by the OS) | Joins the demo frames into `site/public/demo/gnomon_demo.mp4` and burns in subtitles (`site/scripts_demo_video.sh`); only the output video is published | https://ffmpeg.org |
| Lighthouse (run once via `npx`, not a dependency) | Apache-2.0 | Performance and accessibility audit of the story site | https://github.com/GoogleChrome/lighthouse |

### Offline pipeline and tests only (`pipeline/environment.yml`, on top of the above)

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
| `vendor/mmgis_sightline/HorizonProfile.py`, `visibility.py`, `sightmap.py` | NASA-AMMOS MMGIS, https://github.com/NASA-AMMOS/MMGIS (plugins/core/backend/Sightline/scripts, commit c54c70f9) | Apache-2.0, Copyright 2020 California Institute of Technology (LICENSE and NOTICE kept) | Guarded GDAL import with a rasterio/pyproj fallback; MOON_ME frame and LT+S aberration; importable wrappers; HorizonProfile also returns the highest point's pixel, x/y and lat/lon. Each change is marked `[Lunar Navigator]` |

## Ideas and inspiration (no code copied)

| Project | Link | What inspired us |
|---|---|---|
| Iftee07/lunar-mission-planner | https://github.com/Iftee07/lunar-mission-planner | "Move a little" ring of nearby points around a target; we sample a lander-specific Gaussian landing ellipse instead |
| Iftee07/lunar-mission-planner (again) | https://github.com/Iftee07/lunar-mission-planner | A plain-English "why" on every verdict, and an equator vs pole comparison preset |
| MdAhbab/PolarWindow | https://github.com/MdAhbab/PolarWindow | Scoring landing dispersion (share of ellipse points that pass); we score every criterion per point. Also "a ± on every number": our countdown windows from LOLA's height error |
| kaizarmerchantt-git/clps-lunar-mission-browser | https://github.com/kaizarmerchantt-git/clps-lunar-mission-browser | Battery state-of-charge track over the mission; a mast-height control (we plot the whole mast curve); a window finder (our Slip Replanner grid) |
| rafaa-sf/L-SEA | https://github.com/rafaa-sf/L-SEA | Long window finder across dates; DSN station tracking of the Moon (we use Skyfield with the shipped DE440s kernel) |

## Research and mission references

- NASA, Artemis HLS overview for Space Apps 2025 (landing criteria, slide "Key Artemis III Landing Requirements": slope < 10° over 100 m, direct-with-Earth comms, surface and approach lighting, land within 100 m): https://ntrs.nasa.gov/api/citations/20250009323/downloads/ArtemisOverview2025IntSPAPPSChallenge.pdf
- M. Sanchez Net, antenna separation for multipath diversity on lunar south pole direct-to-Earth links, JPL IPN Progress Report 42-243 (2025), cited for low-elevation multipath fades: https://ipnpr.jpl.nasa.gov/progress_report/42-243/42-243A.pdf
- JPL LRO–DSN multipath measurement campaign near the lunar south pole, IPN Progress Reports 42-222 (2020) and 42-226 (2021): https://ipnpr.jpl.nasa.gov/progress_report/42-222/42-222C.html, https://ipnpr.jpl.nasa.gov/progress_report/42-226/42-226D.html
- Other references are listed in `docs/plan/competitive-analysis.md` and added here as features use them.

- Bertone, S., McKenna, T. E., Barker, M. K., Mazarico, E., Beyer, R. A., and Petro, N., Enhanced Topography Models for selected Lunar South Pole regions with Shape-from-Shading, PSJ, doi:10.3847/PSJ/ae5b70; data PGDA product 104 / Zenodo doi:10.5281/zenodo.17954508 (CC BY 4.0). Only the archive README (region bounds) was read: it showed no region covers the IM-2 site, so no DEM was downloaded: https://pgda.gsfc.nasa.gov/products/104
- LROC, "IM-2 Athena Seen Obliquely" (Athena on its side in a 20 m crater; resting coordinates): https://lroc.im-ldi.com/images/1408
- Associated Press, Athena ~250 m (820 ft) from its target, in a crater (as syndicated): https://www.expressandstar.com/world-news/private-lunar-lander-dead-after-landing-in-crater-near-moons-south-pole-5717533
- Gizmodo, Intuitive Machines' explanation (long shadows and dim polar lighting confused navigation): https://gizmodo.com/intuitive-machines-reveals-why-its-moon-lander-faceplanted-into-a-crater-2000602752
- Wikipedia (facts only, quoted and linked on the Evidence page): end-of-mission statements for Chandrayaan-3, IM-1, IM-2 and Blue Ghost Mission 1 (`pipeline/hindcast.yaml`)

## AI assistance

Code is written with Claude Code (Anthropic) from prompts by the team; the team reviews and tests it and is responsible for all of it.
