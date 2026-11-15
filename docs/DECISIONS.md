# Decisions log

One line each: decision + why. Written during the autonomous run of Phases 4–9 (15 Nov 2026).

- Phase 4: build state is a gitignored `data/derived/.build_state.json`; a fresh clone rebuilds everything once. Why: mtimes differ per clone, and committing a cache of local fingerprints would mislead.
- Phase 4: ran `build_all --mark-clean` once on the Phase 3 outputs (commit f38bf1e) instead of re-running the 28-minute ellipse step. Why: those outputs were built by the same code and inputs a moment earlier; the override says not to re-run it unless inputs change.
- Phase 4: step fingerprints hash the source of the specific functions a step runs, not whole modules. Why: later phases add code to `pipeline/horizon.py`, and that must not retrigger the 28-minute tile build.
- Phase 4: the neighbourhood check uses a 420 m radius for every site (the radius quoted for Blue Moon MK1 in the brief), on the same NASA map as the point comparison. Why: one radius keeps the Evidence table comparable across sites.
