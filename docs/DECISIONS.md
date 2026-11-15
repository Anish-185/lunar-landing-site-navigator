# Decisions log

One line each: decision + why. Written during the autonomous run of Phases 4–9 (15 Nov 2026).

- Phase 4: build state is a gitignored `data/derived/.build_state.json`; a fresh clone rebuilds everything once. Why: mtimes differ per clone, and committing a cache of local fingerprints would mislead.
- Phase 4: ran `build_all --mark-clean` once on the Phase 3 outputs (commit f38bf1e) instead of re-running the 28-minute ellipse step. Why: those outputs were built by the same code and inputs a moment earlier; the override says not to re-run it unless inputs change.
- Phase 4: step fingerprints hash the source of the specific functions a step runs, not whole modules. Why: later phases add code to `pipeline/horizon.py`, and that must not retrigger the 28-minute tile build.
- Phase 4: the neighbourhood check uses a 420 m radius for every site (the radius quoted for Blue Moon MK1 in the brief), on the same NASA map as the point comparison. Why: one radius keeps the Evidence table comparable across sites.
- Phase 5: "sunlit" = any part of the Sun's disc visible (eff_sun > 0), matching NASA's AVGVISIB definition; power uses the partial fraction. Why: one definition across the Evidence page and the scores.
- Phase 5: default approach heading 180° (descent along the local meridian toward the pole). Why: the prompt says "descent along the local meridian"; southbound is the natural polar approach. User-editable in the app.
- Phase 5: ellipse odds use the 200 precomputed points (not n=500). Why: the override says to use the precomputed ellipse points; each has its own horizon.
- Phase 5: odds criteria = slope ≤ 10° (NASA), battery survives, link ≥ 50% of the mission (illustrative), Sun visible at touchdown. Why: NASA's slide lists slope, DWE comms and lighting; 50% is our placeholder, editable.
- Phase 5: countdown uncertainty uses the ellipse's p95 LOLA height error as σ_z at the occluder. Why: costs minutes and uses real NASA error data; the occluder's own error is not in our cached windows (logged as a limit).
- Phase 5: comm bands cite JPL IPN PR 42-243/42-222/42-226 for the multipath rationale, but the 2°/5° numbers are ours. Why: the papers give fade depths, not thresholds.
- Phase 6: product name "Gnomon" (the shadow-casting pin of a sundial; at the pole the terrain is the sundial and the Sun circles it). Checked: no GitHub repo for "gnomon lunar/moon", not in the competitor list.
- Phase 6: generic precision lander battery raised from 20 kWh to 50 kWh (illustrative). Why: with a 1000 W night load the old value gave ~16 h of reserve and every polar site failed, so the preset could not distinguish sites. Still labelled "illustrative - edit me".
- Phase 6: tile step fingerprint now hashes only each site's (lander, ellipse sigma), and the ephemeris/horizon/PSR/validation steps only `sites.yaml`; re-marked the tile step clean once (outputs depend only on sigma, unchanged). Why: editing illustrative power numbers must not rerun 28 minutes of horizons.
- Phase 6: default scenario Nobile Rim 2, 12 Jan 2027 12:00 UTC. Why: Go/Go with a named blocking ridge (Scott, 38 km) shows every feature; 00:00 had the landing zone still in shadow.
- Phase 6: navigation at the top (st.navigation position="top"), sidebar holds only the scenario. Why: the sidebar was crowded and the top bar reads like a console.
- Phase 6: Map labels only the selected site (others on hover). Why: ten sites within ~100 km of the pole overlapped.
- Phase 6: media processed with rasterio/GDAL (WEBP/JPEG drivers) instead of adding Pillow. Why: no new dependency or license to vet. Blue Marble taken from NASA SVS 2915 because eoimages.gsfc.nasa.gov timed out.
- Phase 6: hindcast end-of-mission facts from Wikipedia (facts only, quoted, linked). Why: NASA pages for CLPS missions don't state end times in one place.
- Phase 7: PGDA product 104 not used: its 13 regions (2022 list) miss Athena by ~30 km (Leibnitz Beta Plateau starts at 85.06°S, Athena is at 84.79°S). Checked from the Zenodo README in minutes, so no 1 GB download. Fallback per the brief: 20 m results plus an explicit "what the map cannot see" step; logged in METHOD limits.
- Phase 7: "250 m" for Athena's miss is AP's reported figure; we also show our 369 m from LROC's coordinates (target published to two decimals). Why: the brief's headline number needed a source, and the two disagree.
- Phase 7: crater shadow in the Athena story uses an illustrative depth/diameter of 0.1–0.2, labelled as such. Why: no DEM resolves the crater; the geometry still shows why the floor was dark at a 2.5° Sun.
- Phase 7: Replanner Plan B only looks at dates on or after the slipped landing. Why: a slipped launch cannot land earlier.
- Phase 7: blame-the-ridge uses a selectbox of every dark period plus a click on the timeline (not only the click). Why: keyboard accessible, and Plotly point clicks on a line are fiddly.
- Phase 8: story-site Big Bang uses three.js points (no tsParticles). Why: three.js is already loaded for the Moon and Earth; one library instead of two.
- Phase 8: the story site reads the app URL from `site/public/config.json` (`appUrl`) at runtime. Why: the user fills it in after deploying Streamlit without touching code; a push redeploys Pages.
- Phase 8: default mission length 7 days (app and the story's slip scenario). Why: about a crewed surface stay; a 14-day default made the illustrative battery fail for reasons unrelated to the site, which hid the slip story.
- Phase 8: Plan B / slip cards rate "No-go" when Sun-and-link < 25 % even if the battery survives. Why: a lander that survives in the dark with no link has not achieved anything.
- Phase 8: the Sun panorama clips peaks above 11° with a fade at the top. Why: a 15° near rim squashed the 2° Sun path into a line; the caption says peaks are cut off.
- Phase 8: on phones the Sun panorama is a 1100 px strip that pans to follow the Sun. Why: 360° in 390 px is unreadable.
- Phase 8: ridge map 0 % cells are described as "pits that never see the Sun". Why: they are NASA's real 0 % cells (21 of 961 in the crop), isolated, so "flanks" would overstate.
