# Method and known limits

Kept up to date with the code (CLAUDE.md rule 7). Each section gives what we compute, which library or NASA product does it, and what it does not model.

Status: Phase 2 (site catalog, ephemeris, validation). Sections marked *planned* describe the intended method; they are rewritten when the code lands.

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

## Terrain horizon (*planned*, Phase 3)

360° horizon (720 azimuths) from the vendored NASA MMGIS Sightline scripts, which handle lunar curvature, polar-stereographic grid convergence and observer height. Near field 0–5 km from the LOLA 20 m DEM, far field 5–200 km from the 80 m DEM. For each azimuth we keep the distance and location of the highest point (the occluder) so dark periods can be attributed to named terrain.

## Visibility, events, comms, power, landing (*planned*, Phases 5–7)

To be written with the code.

## Known limits

- Azimuth "local north" is undefined exactly at a pole; behaviour for sites within a few metres of ±90° latitude has not been checked yet.
- Terrain comes from LOLA DEMs (20 m / 80 m, plus 5 m shape-from-shading tiles where available). Features smaller than a few DEM pixels (boulders, small craters) are not in the horizon.
- **Custom sites use coarser terrain (160 m) than catalog sites (20 m near field + 80 m far field).** Ridges and crater rims narrower than a few hundred metres are smoothed out, so near-field horizons at custom sites are lower and less detailed; the UI labels them "coarser terrain (160 m) than catalog sites". The 1 m height rounding is negligible next to that (at 1 km it changes the horizon by under 0.03°).
- Terrain coverage ends at 80°S (the edge of the PGDA 90 mosaics). Horizons for sites near that edge miss terrain beyond it.
- Artemis region coordinates are centres measured from NASA's map (a few km uncertainty), and the Blue Moon MK1 and Chang'e-7 targets are unofficial; lander presets are illustrative unless a source is cited.
- Elevations are above the smooth 1737.4 km sphere: no terrain yet (Phase 3), no refraction (there is no atmosphere). The observer is at height 0 unless a mast height is given.
- Comm-quality thresholds are assumptions (user-editable), not a link budget.
