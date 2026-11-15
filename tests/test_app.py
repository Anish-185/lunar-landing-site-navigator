"""Streamlit AppTest smoke tests: every page renders, and the tricky interactions don't raise."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
PAGES = sorted((APP / "views").glob("*.py"))


def _run(path, **qp):
    at = AppTest.from_file(str(path), default_timeout=180)
    for k, v in qp.items():
        at.query_params[k] = v
    return at.run()


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_page_renders(page):
    at = _run(page)
    assert not at.exception, [e.message for e in at.exception]


def test_compare_with_the_same_site_twice():
    """Regression: two scenarios on the same site gave duplicate column labels and a Styler KeyError."""
    at = _run(APP / "views" / "compare.py", site="artemis_nobile_rim_2")
    at.selectbox(key="cmp_site_2").set_value("artemis_nobile_rim_2").run()
    assert not at.exception, [e.message for e in at.exception]


def test_url_reproduces_the_scenario_and_expert_mode():
    at = _run(APP / "views" / "site.py", site="change_7_target", t="2027-03-01T06:00Z", days="7", mast="10",
              mode="expert")
    assert not at.exception
    assert at.session_state["site"] == "change_7_target" and at.session_state["days"] == 7
    assert at.query_params["mast"] in ("10", ["10"]) and len(at.metric) >= 6


def test_custom_site_is_labelled_coarser():
    at = _run(APP / "views" / "site.py", site="custom", lat="-89.45", lon="-137.3")
    assert not at.exception
    assert any("Coarser terrain (160 m)" in m.value for m in [*at.markdown, *at.caption])


def test_decision_brief_and_equator_vs_pole():
    at = _run(APP / "views" / "site.py")
    at.button[[b.label for b in at.button].index("Prepare the decision brief")].click().run()
    assert not at.exception
    doc = at.session_state["brief_html"]
    assert doc.startswith("<!doctype html>") and "Verdict" in doc and "Plan B" in doc and "Sources" in doc
    cmp_ = _run(APP / "views" / "compare.py")
    cmp_.button[0].click().run()
    assert not cmp_.exception and cmp_.session_state["cmp_site_0"] == "apollo_11"


def test_map_thermal_layer_and_site_thermal_line():
    at = _run(APP / "views" / "map.py")
    assert not at.exception
    layer = at.segmented_control(key="map_layer")
    assert "Max temperature" in layer.options
    layer.set_value("Max temperature").run()
    assert not at.exception
    site = _run(APP / "views" / "site.py", site="artemis_haworth")
    assert any("Diviner" in c.value for c in site.caption)


def test_relay_toggle_from_the_url():
    at = _run(APP / "views" / "site.py", relay="1")
    assert not at.exception and at.session_state["relay"] is True
    assert any("Relay assumed" in m.value for m in at.markdown)


def test_no_auto_discovered_pages_folder():
    """Regression: an app/pages/ folder makes Streamlit register old-style pages that bypass the Home.py router
    when someone opens a deep link (e.g. /map) on a fresh server."""
    assert not (APP / "pages").exists()
    assert len(PAGES) == 6  # Site, Compare, Slip Replanner, Map, Athena replay, Evidence
