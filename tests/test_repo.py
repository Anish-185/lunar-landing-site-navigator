"""Repo guardrails from CLAUDE.md: importable modules, small derived files, attributed dependencies,
and an app that never needs the pipeline-only packages."""

import ast
import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MAX_DERIVED_BYTES = 50 * 1024 * 1024
# Never imported by the deployed app, even indirectly (CLAUDE.md working notes).
NEVER_IN_APP = {"osgeo", "geopandas", "shapely", "pyogrio", "fiona"}
# Not in requirements.txt either, so app/ and navigator/ must not import them directly.
PIPELINE_ONLY = NEVER_IN_APP | {"astroquery", "numba", "joblib", "rioxarray", "xarray", "pytest"}


def _modules(package: str) -> list[str]:
    return [f"{package}.{p.stem}" for p in sorted((ROOT / package).glob("*.py")) if p.stem != "__init__"]


@pytest.mark.parametrize("module", _modules("navigator") + _modules("pipeline"))
def test_module_imports(module):
    importlib.import_module(module)


def test_derived_files_under_50_mb():
    too_big = [
        f"{p.relative_to(ROOT)} ({p.stat().st_size / 1e6:.1f} MB)"
        for p in (ROOT / "data" / "derived").rglob("*")
        if p.is_file() and p.stat().st_size >= MAX_DERIVED_BYTES
    ]
    assert not too_big, f"data/derived files must be < 50 MB: {too_big}"


def _dependency_names() -> list[str]:
    lines = (ROOT / "requirements.txt").read_text().splitlines()
    env = yaml.safe_load((ROOT / "pipeline" / "environment.yml").read_text())
    lines += [d for d in env["dependencies"] if isinstance(d, str)]
    names = []
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            names.append(re.split(r"[\[=<>!~ ]", line, maxsplit=1)[0].lower())
    return sorted(set(names) - {"python", "pip"})


def test_every_dependency_is_attributed():
    attributions = (ROOT / "ATTRIBUTIONS.md").read_text().lower()
    missing = [n for n in _dependency_names() if n not in attributions]
    assert not missing, f"add these to ATTRIBUTIONS.md: {missing}"


def test_app_and_navigator_source_never_import_pipeline_only_packages():
    offenders = []
    for path in sorted((ROOT / "app").rglob("*.py")) + sorted((ROOT / "navigator").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            offenders += [f"{path.relative_to(ROOT)}: {n}" for n in names if n.split(".")[0] in PIPELINE_ONLY]
    assert not offenders, f"pipeline-only imports in app code: {offenders}"


def test_running_the_app_never_loads_gdal_geopandas_or_shapely():
    script = f"""
import importlib, sys
from pathlib import Path
from streamlit.testing.v1 import AppTest
root = Path({str(ROOT)!r})
for p in sorted((root / "navigator").glob("*.py")):
    importlib.import_module("navigator." + p.stem)
for page in [root / "app" / "Home.py", *sorted((root / "app" / "pages").glob("*.py"))]:
    at = AppTest.from_file(str(page), default_timeout=60).run()
    assert not at.exception, (page.name, [e.message for e in at.exception])
print(sorted({{m.split(".")[0] for m in sys.modules}} & set({sorted(NEVER_IN_APP)!r})))
"""
    out = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    assert out.stdout.strip().splitlines()[-1] == "[]", f"app loaded: {out.stdout.strip()}"
