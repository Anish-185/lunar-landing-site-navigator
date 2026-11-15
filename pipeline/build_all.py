"""Build everything in data/derived/ from data/raw/ (`make derived`), incrementally.

Each step declares its inputs: the source of the Python functions it runs (so editing an unrelated function in the
same module does not trigger it) and the files it reads. A step is skipped when its input fingerprint matches the
last successful run (stored in data/derived/.build_state.json, gitignored) and its outputs exist. FORCE=1 (or
--force) rebuilds everything; --only STEP runs named steps; --mark-clean records the current fingerprints without
running anything (use only when the outputs are known to be current, e.g. right after a full build).

Fingerprints: content hash (SHA-256) for files under 64 MB, size + mtime for bigger ones (the raw DEMs).
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
RAW = ROOT / "data" / "raw"
STATE = DERIVED / ".build_state.json"
HASH_LIMIT = 64 << 20


@dataclass
class Step:
    name: str
    run: Callable[[], object]
    code: list = field(default_factory=list)       # functions/modules whose source is an input
    inputs: list = field(default_factory=list)     # paths or glob patterns relative to ROOT
    outputs: list = field(default_factory=list)    # paths or glob patterns relative to ROOT (each must match)
    report: Callable[[object], str] | None = None
    extra: Callable[[], str] | None = None         # extra input value (e.g. the few config fields a step uses)


def _files(patterns) -> list[Path]:
    out = []
    for pat in patterns:
        out += sorted(ROOT.glob(pat)) if any(c in pat for c in "*?[") else [ROOT / pat]
    return out


def _file_stamp(p: Path) -> str:
    if not p.exists():
        return "missing"
    st = p.stat()
    if st.st_size > HASH_LIMIT:
        return f"size={st.st_size};mtime={st.st_mtime_ns}"
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fingerprint(step: Step) -> str:
    h = hashlib.sha256()
    for obj in step.code:
        h.update(inspect.getsource(obj).encode())
    for p in _files(step.inputs):
        h.update(f"{p.relative_to(ROOT)}:{_file_stamp(p)}\n".encode())
    if step.extra:
        h.update(step.extra().encode())
    return h.hexdigest()


def outputs_exist(step: Step) -> bool:
    for pat in step.outputs:
        if any(c in pat for c in "*?["):
            if not list(ROOT.glob(pat)):
                return False
        elif not (ROOT / pat).exists():
            return False
    return True


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True))


def _tile_landers() -> str:
    from pipeline.sites import load_landers, load_sites

    landers = load_landers()
    return json.dumps({s["id"]: [s["lander"], landers[s["lander"]]["ellipse_sigma_m"]] for s in load_sites()
                       if s["in_polar_dem"]}, sort_keys=True)


def steps() -> list[Step]:
    # Imported here so `--help` and the state helpers work without the pipeline's heavy dependencies.
    from navigator import engine, geo
    from pipeline import ephem, export_site, horizon, layers, media, sites
    from vendor.mmgis_sightline import HorizonProfile

    cfg = ["pipeline/sites.yaml"]  # landers.yaml feeds only the tile step, through _tile_landers
    site_code = [sites]
    hz_code = [horizon.window_path, horizon.cache_windows, horizon._sample, horizon.two_field_horizon,
               horizon.smooth_sphere_horizon, horizon.site_horizon, HorizonProfile, geo.name_points,
               geo.latlon_to_xy, geo.xy_to_latlon]
    return [
        Step("coarse_dem", horizon.build_coarse_dem, [horizon.build_coarse_dem],
             ["data/raw/pgda90/LDEM_80S_80MPP_ADJ.TIF"], ["data/derived/dem_80s_160m.tif"]),
        Step("ephemeris", ephem.build_all, [ephem.build_site, ephem.build_all, ephem.hourly_utc, ephem.ship_kernels,
                                            engine.sun_earth_azel, *site_code],
             cfg + ["data/raw/kernels/*"], ["data/derived/ephem/*.parquet", "data/derived/kernels/de440s.bsp"]),
        Step("horizons_validation", ephem.write_validation,
             [ephem.write_validation, ephem.horizons_residuals, ephem._separation, engine.sun_earth_azel],
             ["tests/fixtures/horizons.csv", "data/derived/kernels/*"], ["data/derived/validation_horizons.csv"],
             report=lambda r: f"max separation {r['sep'].max():.2e} deg over {len(r)} comparisons"),
        Step("features", horizon.build_features, [horizon.build_features],
             ["data/raw/usgs/MOON_nomenclature_center_pts.zip"], ["data/derived/lunar_features.csv"]),
        Step("site_horizons", horizon.build_site_horizons,
             [horizon.build_site_horizon, horizon.build_site_horizons, *hz_code, *site_code],
             cfg + ["data/raw/windows/*", "data/raw/pgda90/LDEM_80S_80MPP_ADJ.TIF", "data/derived/lunar_features.csv"],
             ["data/derived/horizons/*.npz"]),
        Step("psr_outlines", horizon.build_psr_outlines, [horizon.build_psr_outlines, horizon._psr],
             ["data/raw/pgda90/LPSR_80S_20MPP_ADJ_1km2.*"], ["data/derived/psr_outlines.geojson"]),
        Step("site_psr", horizon.site_psr_table, [horizon.site_psr_table, horizon.psr_distances, *site_code],
             cfg + ["data/raw/pgda90/LPSR_80S_20MPP_ADJ_1km2.*", "data/derived/dem_80s_160m.tif"],
             ["data/derived/site_psr.csv"]),
        # Tiles use landers.yaml only for each site's ellipse sigma: hash that, not the whole file, so editing
        # illustrative power numbers does not rerun the 28-minute step.
        Step("tiles", horizon.build_tiles,
             [horizon.build_tiles, horizon.ellipse_points, horizon._one_point, horizon.psr_distances, *hz_code,
              *site_code],
             ["pipeline/sites.yaml", "data/raw/windows/*", "data/raw/pgda90/LDEM_80S_80MPP_ADJ.TIF",
              "data/raw/pgda90/LPSR_80S_20MPP_ADJ_1km2.*", "data/derived/lunar_features.csv"],
             ["data/derived/tiles/*.npz"],
             report=lambda t: f"{len(t)} sites", extra=_tile_landers),
        Step("avgvisib_validation", horizon.validate_avgvisib,
             [horizon.validate_avgvisib, horizon._visible_fractions, engine.sun_earth_azel, *site_code],
             cfg + ["data/derived/horizons/*.npz", "data/raw/pgda69/*.TIF", "data/derived/kernels/*"],
             ["data/derived/validation_avgvisib.csv"],
             report=lambda av: f"sites over 10 points: {list(av.loc[av['flag_over_10pct'], 'site_id'])}"),
        Step("avgvisib_neighbourhood", horizon.avgvisib_neighbourhood,
             [horizon.avgvisib_neighbourhood, *site_code],
             cfg + ["data/raw/pgda69/*.TIF", "data/derived/validation_avgvisib.csv"],
             ["data/derived/validation_avgvisib_range.csv"]),
        Step("map_layers", layers.build_map_layers, [layers.build_map_layers],
             ["data/raw/pgda69/AVGVISIB_75S_120M_201608*.TIF"], ["data/derived/map_avgvisib.npz"]),
        Step("tile_relief", layers.build_tile_relief, [layers.build_tile_relief, *site_code],
             ["pipeline/sites.yaml", "data/raw/windows/*_ldem_20m.tif"], ["data/derived/relief/*.npz"]),
        Step("shadow_snapshots", export_site.build_shadow_snapshots,
             [export_site.build_shadow_snapshots, horizon.shadow_snapshot, *site_code],
             ["pipeline/sites.yaml", "data/raw/windows/*_ldem_20m.tif", "data/derived/horizons/*.npz"],
             ["data/derived/shadow/*.npz"]),
        Step("story_data", export_site.build_story_data, [export_site],
             ["pipeline/sites.yaml", "pipeline/landers.yaml", "pipeline/hindcast.yaml", "navigator/*.py",
              "data/derived/horizons/*.npz", "data/derived/tiles/*.npz", "data/derived/relief/*.npz",
              "data/derived/validation_*.csv", "data/derived/shadow/*.npz", "data/raw/pgda69/AVGVISIB_85S_060M_201608.TIF"],
             ["site/public/data/story.json"]),
        Step("media", media.build, [media],
             ["data/raw/media/*", "data/derived/dem_80s_160m.tif"],
             ["app/static/nebula.webp", "site/public/media/moon_color.jpg", "site/public/media/earth.jpg",
              "site/public/media/pole_hillshade.webp"]),
    ]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="rebuild every step (same as FORCE=1)")
    ap.add_argument("--only", nargs="*", help="run only these steps (still skipped if clean, unless --force)")
    ap.add_argument("--mark-clean", action="store_true", help="record fingerprints without running")
    ap.add_argument("--list", action="store_true", help="list steps and whether each is clean")
    args = ap.parse_args(argv)
    force = args.force or os.environ.get("FORCE", "") not in ("", "0")

    state, t_all = load_state(), time.time()
    for step in steps():
        if args.only and step.name not in args.only:
            continue
        fp = fingerprint(step)
        clean = state.get(step.name) == fp and outputs_exist(step)
        if args.list:
            print(f"{step.name:24s} {'clean' if clean else 'DIRTY'}")
            continue
        if args.mark_clean:
            state[step.name] = fp
            print(f"{step.name}: marked clean")
            continue
        if clean and not force:
            print(f"{step.name}: up to date, skipped", flush=True)
            continue
        t0 = time.time()
        result = step.run()
        print(f"{step.name}: {time.time() - t0:.1f} s", flush=True)
        if step.report:
            print(f"  {step.report(result)}")
        state[step.name] = fingerprint(step)  # re-read: a step may have written its own inputs (e.g. windows)
        save_state(state)
    if args.mark_clean:
        save_state(state)
    print(f"total {time.time() - t_all:.1f} s")


if __name__ == "__main__":
    main()
