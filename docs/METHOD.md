# Method and known limits

Kept up to date with the code (CLAUDE.md rule 7). Each section gives what we compute, which library or NASA product does it, and what it does not model.

Status: Phase 0 (scaffold). Sections marked *planned* describe the intended method; they are rewritten when the code lands.

## Conventions

- Time: UTC everywhere.
- Body-fixed frame: `MOON_ME` (mean Earth / polar axis), the frame of the LOLA DEMs. Lunar orientation from the DE440 lunar PCK (`moon_pa_de440_200625.bpc`) and the `MOON_ME` frame kernel.
- Coordinates: planetocentric latitude, east-positive longitude, degrees; reference sphere radius 1737.4 km.
- Azimuth: compass, 0° = local north (direction of increasing latitude), 90° = east. Elevation is above the local horizontal plane of the reference sphere.
- Aberration correction for Sun and Earth directions: `LT+S` (light time plus stellar aberration).

## Ephemeris (*planned*, Phase 2)

Sun and Earth azimuth, elevation and range for an observer on the surface come from `spiceypy.azlcpo` with NAIF generic kernels. Angular radius = asin(R / range), with R = 696,000 km (Sun) and 6,371 km (Earth). Checked against JPL Horizons topocentric az/el; the residuals go on the Evidence page.

## Terrain horizon (*planned*, Phase 3)

360° horizon (720 azimuths) from the vendored NASA MMGIS Sightline scripts, which handle lunar curvature, polar-stereographic grid convergence and observer height. Near field 0–5 km from the LOLA 20 m DEM, far field 5–200 km from the 80 m DEM. For each azimuth we keep the distance and location of the highest point (the occluder) so dark periods can be attributed to named terrain.

## Visibility, events, comms, power, landing (*planned*, Phases 5–7)

To be written with the code.

## Known limits

- Azimuth "local north" is undefined exactly at a pole; behaviour for sites within a few metres of ±90° latitude has not been checked yet.
- Terrain comes from LOLA DEMs (20 m / 80 m, plus 5 m shape-from-shading tiles where available). Features smaller than a few DEM pixels (boulders, small craters) are not in the horizon.
- Site coordinates for Artemis candidate regions are approximate region centres; lander presets are illustrative unless a source is cited.
- Comm-quality thresholds are assumptions (user-editable), not a link budget.
