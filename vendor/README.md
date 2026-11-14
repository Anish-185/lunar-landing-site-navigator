# vendor/

Third-party code we ship with the project (CLAUDE.md rule 4). Each vendored project gets its own folder with:

- the project's original `LICENSE` (and `NOTICE`, if it has one), unmodified;
- a header at the top of every file naming the source (repo URL, path, commit) and listing our changes;
- a row under "Vendored code" in `ATTRIBUTIONS.md`.

Only MIT, BSD, Apache-2.0 or ISC code may be vendored. Planned: `mmgis_sightline/` (NASA-AMMOS MMGIS Sightline scripts, Apache-2.0) in Phase 3.
