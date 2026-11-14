# Method and known limits

Kept up to date with the code (CLAUDE.md rule 7). Each section gives what we compute, which library or NASA product does it, and what it does not model.

Status: Phase 1 (data). Sections marked *planned* describe the intended method; they are rewritten when the code lands.

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

## Ephemeris (*planned*, Phase 2)

Sun and Earth azimuth, elevation and range for an observer on the surface come from `spiceypy.azlcpo` with NAIF generic kernels. Angular radius = asin(R / range), with R = 696,000 km (Sun) and 6,371 km (Earth). Checked against JPL Horizons topocentric az/el; the residuals go on the Evidence page.

## Terrain horizon (*planned*, Phase 3)

360° horizon (720 azimuths) from the vendored NASA MMGIS Sightline scripts, which handle lunar curvature, polar-stereographic grid convergence and observer height. Near field 0–5 km from the LOLA 20 m DEM, far field 5–200 km from the 80 m DEM. For each azimuth we keep the distance and location of the highest point (the occluder) so dark periods can be attributed to named terrain.

## Visibility, events, comms, power, landing (*planned*, Phases 5–7)

To be written with the code.

## Known limits

- Azimuth "local north" is undefined exactly at a pole; behaviour for sites within a few metres of ±90° latitude has not been checked yet.
- Terrain comes from LOLA DEMs (20 m / 80 m, plus 5 m shape-from-shading tiles where available). Features smaller than a few DEM pixels (boulders, small craters) are not in the horizon.
- **Custom sites use coarser terrain (160 m) than catalog sites (20 m near field + 80 m far field).** Ridges and crater rims narrower than a few hundred metres are smoothed out, so near-field horizons at custom sites are lower and less detailed; the UI labels them "coarser terrain (160 m) than catalog sites". The 1 m height rounding is negligible next to that (at 1 km it changes the horizon by under 0.03°).
- Terrain coverage ends at 80°S (the edge of the PGDA 90 mosaics). Horizons for sites near that edge miss terrain beyond it.
- Site coordinates for Artemis candidate regions are approximate region centres; lander presets are illustrative unless a source is cited.
- Comm-quality thresholds are assumptions (user-editable), not a link budget.
