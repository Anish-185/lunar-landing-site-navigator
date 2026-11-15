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
