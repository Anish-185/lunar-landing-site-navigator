# Method and known limits

Kept up to date with the code (CLAUDE.md rule 7). Each section gives what we compute, which library or NASA product does it, and what it does not model.

Status: Phase 8 (story site, decision brief, educator extras, deployment) on the Phase 3–7 pipeline, engine and app. Sections marked *planned* describe the intended method; they are rewritten when the code lands.

## Conventions

- Time: UTC everywhere.
- Body-fixed frame: `MOON_ME` (mean Earth / polar axis), the frame of the LOLA DEMs. Lunar orientation from the DE440 lunar PCK (`moon_pa_de440_200625.bpc`) and the `MOON_ME` frame kernel.
- Coordinates: planetocentric latitude, east-positive longitude, degrees; reference sphere radius 1737.4 km.
- Azimuth: compass, 0° = local north (direction of increasing latitude), 90° = east. Elevation is above the local horizontal plane of the reference sphere.
- Aberration correction for Sun and Earth directions: `LT+S` (light time plus stellar aberration).

## Data (Phase 1)

`make data` (`pipeline/fetch_data.py`) downloads into `data/raw/`; sources and citations are in `ATTRIBUTIONS.md`.

| Data | Resolution | How we get it |
| --- | --- | --- |
| LOLA DEM, slope, height error, 80°S–90°S (PGDA 90) | 80 m | downloaded |
| LOLA DEM and slope (PGDA 90) | 20 m | not downloaded (2.7 and 3.8 GB): `navigator.geo.read_window` reads only the window it needs, over HTTP range requests (GDAL `/vsicurl/`). The files are tiled (512×512) and compressed, so a 10 km window costs a few tiles. |
| PSRs > 1 km² shapefile (PGDA 90) | from 20 m | downloaded |
| Average Sun / Earth visibility, 85°S and 75°S (PGDA 69) | 60 m, 120 m | downloaded (plain GeoTIFFs; the product page's `_COG` links are dead). int16 with scale factor 4e-5: stored value × 4e-5 = visible fraction 0–1, averaged over 18.6 years |
| NAIF kernels: DE440s, lunar PA orientation, `MOON_ME` frame, leap seconds | — | downloaded |

All the LOLA rasters share one CRS: south polar stereographic, true scale at the pole, on the 1737.4 km sphere (`+proj=stere +lat_0=-90 +lat_ts=-90 +R=1737400`). `navigator.geo` reads it from each file; nothing is hardcoded. Heights are metres above that sphere.

**Shipped DEM for custom sites.** `data/derived/dem_80s_160m.tif` is the 80 m DEM averaged over exact 2×2 blocks (160 m), rounded to whole metres and stored as int16 (nodata −32768), tiled and DEFLATE-compressed. Catalog sites use precomputed horizons from the 20 m and 80 m DEMs. Custom lat/lon sites compute their horizon in the app from this 160 m DEM with the vendored MMGIS HorizonProfile script, running on rasterio/pyproj stand-ins for the few GDAL/OSR calls it makes (`navigator.geo.gdal_compat`, `osr_compat`), so the deployed app needs no GDAL.

## Site catalog (Phase 2)

`pipeline/sites.yaml` holds 17 sites; every coordinate cites the page it came from (`source_url`), and `pipeline/sites.py` rejects entries without one. Mission sites use published positions: LROC for IM-1 and IM-2 (target and resting spot), ISRO via Wikipedia for Chandrayaan-3, LROC/NSSDC for Blue Ghost 1, NSSDC (Wagner et al. 2017) for Apollo 11.

Three kinds of site are approximate, and their notes say so:

- **Artemis III regions.** NASA publishes no coordinates, only a map (release 24-136, 28 Oct 2024). We measured each box centre on that map: pixels → polar stereographic x/y using the map's pole marker and 50 km scale bar (0.2778 km/px) → lat/lon in our CRS. Checks: the boxes drawn on a LOLA hillshade sit on the same craters as in NASA's figure; IM-2's published target falls inside the Mons Mouton Plateau box; two published best-site points (arXiv 2406.19863) fall inside the Nobile Rim 2 and de Gerlache Rim 2 boxes, ~8–9 km from our centres. Expect errors of a few km; boxes are ~21 km across.
- **Blue Moon MK1.** NASA says only "Shackleton Connecting Ridge". We use the Connecting Ridge candidate site of Gracy & Lee (LPSC 2024): 89.53432°S, 150.05233°W.
- **Chang'e-7.** 88.8°S, 123.4°E ("peak near the southeast ridge of Shackleton"); no final site has been announced.

Three sites lie outside the south polar DEMs (Chandrayaan-3 at 69°S, Blue Ghost 1 and Apollo 11 near the equator), so they get ephemerides but no terrain horizon yet (`in_polar_dem` is false).

Lander presets (`pipeline/landers.yaml`): every number has a source entry, either a citation with URL or "illustrative - edit me". Cited so far: cruise times of Nova-C, Blue Ghost and Vikram (launch to landing), Vikram's 738 W lander power, and the Artemis 100 m landing requirement behind the generic precision lander's 33 m sigma (100 m / 3, our assumption). Everything else is illustrative.

## Ephemeris (Phase 2)

`navigator.engine.sun_earth_azel` gives Sun and Earth azimuth, elevation and range for a point on the 1737.4 km sphere, using `spiceypy.azlcpo(method="ELLIPSOID", abcorr="LT+S", azccw=False, elplsz=True, obsctr="MOON", obsref="MOON_ME")`. The observer position comes from `spiceypy.latrec`. Kernels: DE440s (Sun, Earth, Moon), the DE440 lunar orientation PCK, the `MOON_ME` frame kernel `moon_de440_250416.tf`, `pck00011.tpc` and `naif0012.tls`. They are shipped in `data/derived/kernels/` (46 MB), so the app computes custom sites with no network. Angular radius = asin(R / range), R = 696,000 km (Sun), 6,371 km (Earth).

`pipeline/ephem.py` runs the same function hourly (UTC) for every catalog site over 2023-08-01–09-30 (Chandrayaan-3), 2024-02-15–03-31 (IM-1), 2025-02-20–03-31 (IM-2, Blue Ghost 1) and 2026-11-01–2028-12-31 (planning): 22,536 epochs per site, 17 sites in ~6 s on 12 cores. Output: `data/derived/ephem/<site_id>.parquet` (utc, sun_az, sun_el, sun_range_km, earth_az, earth_el, earth_range_km), angles and ranges in float32 (precision ~3e-5° and < 20 km, both negligible).

**Validation against JPL Horizons.** Apparent AZ/EL from Horizons (observer on body 301 at the site, elevation 0, no refraction, UT time scale) for Apollo 11, the Shackleton rim (Chang'e-7 site) and Malapert at 20 epochs spread over 2027, plus the Athena site at 5 epochs on 2025-03-06: 130 comparisons. **Largest angular separation: 8.5e-7° (0.003 arcsec) for both the Sun and Earth**, which is the precision Horizons prints. We use the same DE440 ephemeris and lunar mean-Earth frame, so the agreement is expected. The responses are cached in `tests/fixtures/horizons.csv` (tests run offline; `pytest -m network` refreshes them); residuals are in `data/derived/validation_horizons.csv` for the Evidence page.

**Sanity checks** (tests, no terrain): at 88.8°S the Sun stays within ±2.75° of the horizon (colatitude 1.2° + the Moon's 1.54° axial tilt), and within ±2.0° at the 89.5°S connecting ridge. Earth there moves between −7.6° and +5.8° with libration and is above the horizon 44% of 2027. At Apollo 11, Earth never drops below 58°, in the western sky (azimuth ≈ 270°).

## Terrain horizon (Phase 3)

**Code.** NASA-AMMOS MMGIS `HorizonProfile.py`, vendored in `vendor/mmgis_sightline/` (Apache-2.0; changes listed in each file's header). For each of 720 azimuths (0.5° apart) it marches outward from the observer over the DEM. The step is 1 pixel near the observer and grows logarithmically with distance. Each sample's height is lowered by the curvature drop d²/2R (R = 1737.4 km), and the march direction is corrected for grid convergence of the polar stereographic map. It keeps the highest elevation angle per azimuth, and we also keep that sample's pixel: the occluder.

**Two fields per site.** Near field 0–5 km from a cached ~11 km window of the 20 m LOLA DEM; far field 5–200 km from the 80 m DEM. The horizon is the higher of the two per azimuth, with the winner's distance, x/y and lat/lon. Both fields use the same eye height (the 20 m surface + mast): MMGIS adds the observer height to its own DEM's surface, so the far-field call gets mast + z(20 m) − z(80 m). Masts 1, 2, 5, 10, 15 and 20 m. Output: `data/derived/horizons/<site_id>.npz`. 17 sites × 6 masts take 26 s.

**Outside the polar DEMs.** Chandrayaan-3 (69°S) uses a 205 km window of PGDA's 240 m DEM of 60–90°S, read remotely once and cached (`horizon_source = ldem_60s_240m`, single field 0–200 km). Blue Ghost 1 and Apollo 11 have no DEM here: their horizon is the smooth-sphere dip −acos(R/(R+h)) (`horizon_source = smooth_sphere`), and the UI must say so.

**Blame the ridge.** Each occluder point is named from the USGS Gazetteer of Planetary Nomenclature: approved craters (including lettered satellite craters such as Cabeus B) and montes, each as a circle of its published diameter. If the point lies inside one or more circles, the smallest wins; otherwise the closest feature within 1.5 radii. The relation is "inside" (< 0.8 R), "rim" (0.8–1.2 R), "near" (≤ 1.5 R), or "on" for a mons. `navigator.geo.blame_line` turns it into e.g. "Sun blocked by the rim of Shackleton, 21 km away at az 212°". Circles are a rough footprint: an occluder on a crater wall can be labelled "inside", and terrain between named features stays unnamed.

## Landing ellipse (Phase 3)

For each polar site, 200 points drawn from a 2-D Gaussian (σ = the site's default lander `ellipse_sigma_m` on each axis, seed 0) in the polar stereographic plane. Each point gets its own full near + far horizon at 2 m (lander deck height, our assumption), with occluder names. It also gets slope from the 20 m LDSM, height error from the 20 m error map, and distance to the nearest PSR. Output: `data/derived/tiles/<site_id>.npz`. The 14 sites take ~28 min on 12 cores, under the 30 min budget, so no far-field shortcut is used.

## Permanently shadowed regions (Phase 3)

Distances are measured in the polar stereographic plane from each site and ellipse point to the nearest PSR > 1 km² in PGDA's `LPSR_80S_20MPP_ADJ_1km2` shapefile (GeoPandas `sjoin_nearest`; 0 inside one). Results are in `data/derived/site_psr.csv` and the tiles. PSRs are identified by their catalog IDs (e.g. `HNP_860121_3378628`). The app draws `data/derived/psr_outlines.geojson`: the same polygons simplified with a 40 m tolerance, in polar stereographic metres (not lon/lat), 2.3 MB. GeoPandas and Shapely run only in the pipeline.

## Shadow snapshot (Phase 3, used in Phase 5)

`shadow_snapshot(site, utc)` runs MMGIS `sightmap.py` (Numba, needs real GDAL, so pipeline only) over a 600 m square at 20 m. Shadows from terrain within 5 km come from the 20 m window. Farther terrain comes from the site's far-field horizon: if the Sun is below it, the whole square is in shadow. Results are cached in `data/derived/shadow/`. At IM-2 Athena's touchdown (2025-03-06 17:28:50 UTC) the Sun was 2.5° up at az 66°, and the whole 600 m square is lit at 20 m resolution. Athena came to rest in a ~20 m crater, smaller than one DEM pixel, so this model cannot show that shadow.

## Validation against NASA's illumination maps (Phase 3)

PGDA product 69's AVGVISIB maps give, per pixel, the fraction of hourly timesteps over 18.6 years (one nutation cycle) in which **any part** of the solar (or Earth) disc is visible (PDS label). Neither the label nor the product page gives the exact window, so we use the 18.6 years ending at the product date: 1998-01-01 to 2016-08-01, 6-hourly (27,148 epochs). We compare at each polar site with our 1 m horizon. "Disc" = disc centre elevation + angular radius above the horizon (like for like); "point" = disc centre only. The 85°S map (60 m) is used for sites south of 85°S, the 75°S map (120 m) otherwise. Results: `data/derived/validation_avgvisib.csv`.

| Site | NASA Sun | Ours (disc) | Δ | NASA Earth | Ours (disc) | Δ |
| --- | --- | --- | --- | --- | --- | --- |
| Haworth | 26.8% | 27.3% | +0.5 | 47.2% | 47.2% | 0.0 |
| Malapert Massif | 31.6% | 30.9% | −0.7 | 19.2% | 11.3% | −7.9 |
| Mons Mouton Plateau | 31.6% | 30.5% | −1.1 | 75.1% | 74.8% | −0.3 |
| Mons Mouton | 6.4% | 6.8% | +0.4 | 34.3% | 30.1% | −4.2 |
| Nobile Rim 1 | 35.1% | 32.4% | −2.7 | 45.9% | 45.9% | 0.0 |
| Nobile Rim 2 | 41.2% | 40.3% | −0.8 | 70.0% | 70.1% | +0.1 |
| de Gerlache Rim 2 | 37.7% | 38.3% | +0.6 | 55.3% | 55.5% | +0.1 |
| Slater Plain | 1.9% | 2.3% | +0.5 | 40.9% | 41.2% | +0.4 |
| IM-2 target | 46.5% | 46.5% | 0.0 | 93.1% | 93.6% | +0.5 |
| IM-2 resting spot | 46.8% | 46.9% | +0.1 | 93.1% | 93.6% | +0.5 |
| IM-1 Odysseus | 35.6% | 36.4% | +0.8 | 100% | 100% | 0.0 |
| Chang'e-7 target | 50.0% | 49.8% | −0.2 | 58.7% | 60.7% | +1.9 |
| **Peak near Cabeus B** | 19.7% | 9.6% | **−10.1** | 7.8% | 0.0% | −7.8 |
| **Blue Moon MK1 (ridge)** | 44.0% | 57.6% | **+13.7** | 51.5% | 53.0% | +1.6 |

12 of 14 sites agree within 2.7 points for the Sun and 7.9 points for Earth; most within 1 point. Treating the Sun as a point instead of a disc lowers our Sun fraction by 1–6 points and Earth by up to 12. Two sites differ by more than 10 points, and both are explained by terrain, not errors:

- **Peak near Cabeus B: DEM resolution.** With our near field on the 80 m DEM instead of 20 m, our Sun fraction rises from 9.6% to 16.8%, toward NASA's 19.7% (120 m DEM): nearby terrain resolved only at 20 m blocks the Sun. NASA's own map varies from 13% to 31% within 840 m of the site.
- **Blue Moon MK1 (connecting ridge): position on a narrow ridge.** NASA's map ranges from 0% to 59.5% within 420 m of the site (crest vs flanks), and our 57.6% is inside that range. Changing the near-field resolution does not move it (57.4%).
- Malapert's Earth difference (−7.9 points) is the same kind: NASA's values range from 0% to 43% within 420 m.

**NASA's own spread within 420 m.** A single-pixel comparison hides how fast long-run sunlight changes on steep terrain, so `horizon.avgvisib_neighbourhood` also reads NASA's minimum and maximum within 420 m of each site (same map) and checks whether our value falls inside: `data/derived/validation_avgvisib_range.csv`. **Sun: ours is inside NASA's own 420 m range at 13 of 14 sites**, including Blue Moon MK1 (NASA 0%–59.5%, ours 57.6%) and Malapert (24.7%–44.4%, ours 30.9%). The exception is Peak near Cabeus B (NASA 13.3%–30.8%, ours 9.6%), explained above by our 20 m near field resolving terrain the 120 m map smooths out. **Earth: inside at 12 of 14**; the two outside miss by under half a point (IM-2 target: ours 93.6%, NASA max 93.1%; Chang'e-7: 60.66% vs 60.64%).

## Build (Phase 4)

`make derived` runs `pipeline/build_all.py`, which is incremental. Each step declares its inputs: the source code of the functions it runs (via `inspect.getsource`, so editing an unrelated function in the same module does not trigger it), the config files (`sites.yaml`, `landers.yaml`) and the data files it reads. A step is skipped when that fingerprint matches its last successful run (stored in `data/derived/.build_state.json`, gitignored) and its outputs exist. Files under 64 MB are fingerprinted by SHA-256 of their content, bigger ones (raw DEMs) by size + mtime. `make derived FORCE=1` rebuilds everything; `python -m pipeline.build_all --list` shows which steps are dirty, `--only STEP` runs one step. A no-change run takes ~1 s; the 28-minute ellipse step reruns only when its code, the site/lander config, the 20 m windows, the 80 m DEM, the PSR shapefile or the feature names change. `tests/test_derived_outputs.py` smoke-checks every committed output.

## Engine (Phase 5)

All in `navigator/`, pure NumPy/pandas, hourly samples. `engine.timeline(site, start, days, mast, lander)` builds one table per scenario; the other modules are small functions over it.

- **Horizon at the body** (`visibility.horizon_at`): periodic linear interpolation of the 720-azimuth horizon at the Sun's/Earth's azimuth. Mast heights between the computed ones (1, 2, 5, 10, 15, 20 m) are interpolated linearly. Clearance = disc-centre elevation − horizon.
- **Visible disc fraction** (`visibility.disc_fraction`): the circle-segment area above a locally straight horizon, f = 1 − (acos c − c√(1−c²))/π with c = clearance / angular radius. "Sunlit" means any part of the disc is visible (f > 0), the same definition as NASA's AVGVISIB maps.
- **Eclipses** (`eclipse.py`): the fraction of the Sun's disc covered by Earth's (two-circle intersection, flat small-angle geometry) at the Sun–Earth separation seen from the site. Effective sun = disc fraction × (1 − eclipse fraction). Check: the total lunar eclipse of 14 Mar 2025 (the one Blue Ghost 1 filmed) shows as 100% cover at the IM-2 site, peaking 14 Mar ~06:00 UTC.
- **Events** (`events.py`): rises/sets from sign changes of clearance, refined by linear interpolation between hourly samples (error ~ minutes); continuous windows, longest night, longest comms blackout.
- **Countdown uncertainty**: the horizon is shifted by ±σ_h = atan(σ_z / d), d = distance to the occluder at the body's azimuth, and the earliest/latest crossing is reported. σ_z is the 95th percentile of the LOLA 20 m height-error map over the site's landing ellipse (0.2–1 m at catalog sites). Limitation: that error is near the site, not at the occluder; custom sites use an illustrative 10 m (160 m DEM smoothing), catalog sites without a tile an illustrative 1 m.
- **Comm quality** (`comms.py`): Earth clearance bands **good ≥ 5°, marginal 2–5°, poor 0–2°, none < 0** — our assumption, user-editable, not a link budget. Rationale: south-pole direct-to-Earth links run at low elevation, where reflections off the lunar surface cause multipath fades of more than 20 dB (JPL IPN Progress Report 42-243, Sanchez Net 2025; LRO–DSN multipath measurements in IPN PR 42-222 and 42-226). DSN: Moon elevation at Goldstone, Madrid and Canberra with Skyfield and the shipped DE440s kernel (no network); a complex counts at ≥ 10°. **Link usable = band marginal or better AND at least one complex in view.** NASA's Artemis III requirements assume direct-with-Earth communication with no relay.
- **Power** (`power.py`): array output = array_W × cos(sun el) (vertical, sun-tracking panel) or sin(sun el) (horizontal) × effective sun. Battery: forward Euler over the hourly samples, clipped to [0, capacity], starting full; survives if it never goes below 20%. All lander numbers are illustrative unless `landers.yaml` cites a source.
- **Scores** (`scores.py`): % sunlit, % link, % both, longest night and blackout, battery survival, eclipses, and plain-English reasons. A dark period is blamed on terrain when the horizon at the body's azimuth is above 0.05° (otherwise "below the horizon"), using the occluder's name, distance and azimuth from Phase 3, e.g. "Sun blocked by the rim of Shackleton, 21 km away at az 212° from 4 Mar 05:00 UTC". For a comms blackout with Earth visible, the reason is low clearance (multipath) or no DSN complex.
- **Landing light** (`landing.landing_light`): Sun elevation and azimuth at touchdown; angle to the approach heading (default 180°, descent along the local meridian toward the pole); "sun in camera" when within 30° of the heading and below 10° elevation; **% of the landing zone in shadow = share of the site's 200 ellipse points whose own horizon at the Sun's azimuth is above the Sun's elevation**; shadow length of a 1 m boulder = 1/tan(el). Rating: bad if the Sun is down or ≥ 50% of the zone is shadowed; caution if sun in camera, ≥ 10% shadowed or the Sun below 1°; good otherwise (thresholds illustrative). Pure NumPy, any time, no GDAL. NASA lists approach lighting and surface lighting among the Artemis III landing requirements.
- **Landing-zone odds** (`landing.ellipse_odds`): the mission is run at each of the 200 precomputed ellipse points with its own horizon (Sun/Earth directions from the site; they change by < 0.01° over 100 m). Pass criteria per point: **slope ≤ 10°** (NASA, "Key Artemis III Landing Requirements": "Surface slope for landing (100m): <10 deg"; our slope is the 20 m LDSM at the point, a shorter baseline than 100 m, so it is conservative); battery stays above 20%; link usable ≥ 50% of the mission (illustrative); Sun visible at touchdown. P(success) = share of points passing all four.


## App (Phase 6)

Streamlit (`app/Home.py` routes to `app/pages/`), Plotly for every chart, no network at runtime. The sidebar scenario (site or custom lat/lon, landing UTC, mission length, mast, lander, approach heading, Simple/Expert) is mirrored in the URL query string, so a copied link reproduces the view. Custom sites in 80–90°S get their horizon in the app from the shipped 160 m DEM through the vendored MMGIS HorizonProfile on the rasterio/pyproj stand-ins (~0.1 s per mast height), labelled "coarser terrain (160 m) than catalog sites". The Map page draws NASA's AVGVISIB maps averaged to 2.5 km (`data/derived/map_avgvisib.npz`, 77 kB) and PSR outlines from `psr_outlines.geojson` (only PSRs > 3 km² are drawn, for speed). The Evidence page shows the Horizons residuals, our long-run Sun/Earth fractions against NASA's value and NASA's own range within 420 m, and a hindcast of four flown landers: our first sunset after landing vs the reported end of the mission (`pipeline/hindcast.yaml`, each quoted from its source). Results: Chandrayaan-3, our sunset 4 Sep 2023 08:49 UTC vs "shut down at sunset … twelve days after landing" (4 Sep); Blue Ghost 1, 16 Mar 2025 20:55 UTC on a smooth sphere vs "about 5 hours after lunar sunset" at 23:25 UTC (sunset ~18:25, so ours is ~2.5 h late, as expected without terrain); IM-1, our sunset 2 Mar 2024 vs last contact 29 Feb (Odysseus lost power earlier than our 2 m terrain sunset); IM-2 ended by power on its side in a crater, not by sunset (ours: 19 Mar).

Design: one stylesheet (`app/style.css`), `.streamlit/config.toml` theme, shared Plotly template `gnomon` in `navigator/plots.py`. Colour carries meaning only: Sun gold, Earth blue, terrain grey, red for no-go/failure; every status also has an icon and a word (Go / Caution / No-go).

## Differentiators (Phase 7)

- **Slip Replanner** (`navigator/replan.py`, page "Slip Replanner"). Landing = launch + cruise (lander preset) + slip. For each candidate site (catalog polar sites, IM-2 target excluded as a duplicate) the hourly timeline is computed once over the slipped landing ± 60 days plus the mission length; every landing date is then a window into it: % Sun and link from the window, battery survival for all dates at once (a dates × hours power matrix through the same battery model). 13 sites × 121 dates take ~4 s. Plan B cards: another site on the slipped day, the same site on a later day, and the best on or after the slipped day (a slipped launch cannot land earlier); ranking = % Sun and link with battery failure pushed to the bottom; ties go to the earliest date. "What changed" diffs the two `scores.summary` results (battery, longest night/blackout ≥ 6 h, sunlit/link ≥ 5 points, eclipses). A test checks that the grid matches a full single-scenario run.
- **Blame the ridge** (Site page). Every night and comms blackout in the mission is listed; clicking the timeline picks the one under the cursor. For a hidden body the reason names the occluder at its azimuth (feature, relation, distance, azimuth); for Earth above the terrain the reason is low clearance (multipath) or no DSN dish. "Show on map" marks the occluder's polar stereographic x/y on the Map page (catalog sites; only for occluders ≥ 500 m away).
- **Landing-zone panel**: `ellipse_odds` over 20 m LOLA relief around the site (`data/derived/relief/<site>.npz`, ±400 m, from the cached 20 m windows), pass = gold circle, fail = red cross with the failed tests on hover, plus per-criterion pass rates.
- **Mast curve**: the same mission with the mast at 1–20 m (horizon interpolated between the computed masts), with NASA's Vertical Solar Array Technology class marked at 10 m.
- **Science vs engineering**: ellipse points and catalog sites, distance to the nearest PSR against % Sun and link; the Pareto frontier (closer to permanent shadow and better lit) is highlighted.
- **Athena replay** (page). Touchdown 2025-03-06 17:28:50 UTC at LROC's resting spot (84.7906°S, 29.1957°E). AP reported Athena about 250 m from its target; LROC's positions (target given to two decimals) differ by 369 m. Sun 2.5° up at az 66°: a 1 m boulder casts a 23 m shadow; 0% of the landing zone is in terrain shadow at 20 m, and the MMGIS sightmap snapshot of the 600 m square is fully lit. Intuitive Machines attributed the navigation error to long shadows and dim polar lighting. A 10-day mission at the 200 points around the target passes all four tests at 100% (upright lander, illustrative Nova-C preset). LROC found Athena on its side in a 20 m crater: one pixel of the 20 m DEM. With an illustrative depth of 0.1–0.2 × diameter, at 2.5° the rim casts a 46–93 m shadow, so the crater floor was dark.
- **PGDA product 104 (5 m shape-from-shading DEMs, Bertone et al.) does not cover Athena.** The archive (Zenodo 10.5281/zenodo.17954508, CC BY 4.0) covers the 13 Artemis III regions of 2022; the nearest, Leibnitz Beta Plateau, spans 85.06–85.79°S, and Athena is at 84.79°S, ~30 km outside it. We checked the region bounds in the archive README before downloading anything. No public DEM we know of resolves Athena's crater, and the story says so.

## Story site and polish (Phase 8)

- **Story site** (`site/`, Vite, static, deployed to GitHub Pages by `.github/workflows/pages.yml`). Every chart and number comes from `site/public/data/story.json`, written by `pipeline/export_site.py` (a `make derived` step) from the same engine: the de Gerlache Rim 2 skyline and the Sun's January 2027 path with its blocking ridges, Earth's libration there, NASA's AVGVISIB cells within 900 m of the Blue Moon MK1 target, the Athena replay numbers, a slip grid (13 sites × 121 days, 7-day stay) and the validation numbers. three.js draws the Big Bang particles and the Moon and Earth (NASA SVS CGI Moon Kit, Blue Marble); it is downloaded at idle and starts on the reader's first scroll, renders only while animating or scrolling. Lenis smooths scrolling, Motion's `scroll()` drives pinned chapters and parallax, Plotly.js draws the charts and loads only when a chart is near. `prefers-reduced-motion` gets a static page with every beat visible. Lighthouse (desktop, local build): performance 100, accessibility 100, best practices 100, SEO 92. The Mission Console embeds the Streamlit app from `site/public/config.json` (`appUrl`), with a placeholder until it is set.
- **Decision brief**: one HTML page (plain f-string template, `navigator/brief.py`) with the scenario, the three verdicts and their reasons, landing-zone odds, Plan B within ±30 days, assumptions and sources; the timeline chart is embedded as Plotly HTML (loads plotly.js from its CDN when opened). Print to PDF from the browser. The hourly CSV is always available.
- **Educator extras**: "Equator vs pole" preset on Compare (Apollo 11 vs the Shackleton rim, same dates) and a short "Why is the pole so strange?" explainer.
- **Accessibility**: every status has an icon and a word as well as a colour; every chart has a caption describing what it shows; keyboard-reachable selection for blame the ridge.
- **Deployment**: `requirements.txt` only at the root; tested in a fresh Python 3.11 venv from a clean clone: all seven pages render under Streamlit's AppTest, no GDAL/GeoPandas/Shapely/Numba/joblib is imported, no network call at startup, every committed file < 50 MB.

## Known limits

- Azimuth "local north" is undefined exactly at a pole; behaviour for sites within a few metres of ±90° latitude has not been checked yet.
- Terrain comes from LOLA DEMs (20 m near field, 80 m far field; 240 m for Chandrayaan-3). Features smaller than a few DEM pixels (boulders, small craters such as the ~20 m crater Athena landed in) are not in the horizons or shadow snapshots. At sites with steep nearby terrain, long-run sunlight can differ from NASA's 60–120 m maps by 10 points or more (see the validation above).
- Blue Ghost 1 and Apollo 11 have no terrain horizon (smooth sphere only); Chandrayaan-3 uses 240 m terrain.
- Occluder names come from circular feature footprints (centre + diameter); complex rims and terrain between named features may be labelled loosely or left unnamed.
- **Custom sites use coarser terrain (160 m) than catalog sites (20 m near field + 80 m far field).** Ridges and crater rims narrower than a few hundred metres are smoothed out, so near-field horizons at custom sites are lower and less detailed; the UI labels them "coarser terrain (160 m) than catalog sites". The 1 m height rounding is negligible next to that (at 1 km it changes the horizon by under 0.03°).
- Terrain coverage ends at 80°S (the edge of the PGDA 90 mosaics). Horizons for sites near that edge miss terrain beyond it.
- Artemis region coordinates are centres measured from NASA's map (a few km uncertainty), and the Blue Moon MK1 and Chang'e-7 targets are unofficial; lander presets are illustrative unless a source is cited.
- Elevations are above the smooth 1737.4 km sphere: no terrain yet (Phase 3), no refraction (there is no atmosphere). The observer is at height 0 unless a mast height is given.
- Orbital terrain misses small craters: Athena's 20 m crater is one pixel of the 20 m LOLA DEM, and PGDA's 5 m SfS DEMs do not cover its site. Landing-light shadow fractions and ellipse odds see only terrain larger than ~40 m.
- Default lander numbers are illustrative: with the generic precision preset (50 kWh, 1000 W) most 7-day polar missions that include a night longer than ~40 h fail the battery test. That is a statement about the preset, not the site.
- Comm-quality thresholds are assumptions (user-editable), not a link budget: no antenna patterns, no fading statistics, no data rates.
- Hourly sampling: events are interpolated between samples (minutes of error); a Sun or Earth glimpse shorter than an hour can be missed.
- Ellipse points use the site's Sun/Earth directions and the 20 m slope (a 20 m baseline, not NASA's 100 m), and a 2 m deck height.
- The battery model is a single bucket (no temperature, no degradation, no heater loads during the night beyond `load_W`).
