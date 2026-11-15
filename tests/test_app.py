"""Streamlit AppTest smoke tests: every page renders, and the tricky interactions don't raise."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
PAGES = sorted((APP / "pages").glob("*.py"))


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
    at = _run(APP / "pages" / "compare.py", site="artemis_nobile_rim_2")
    at.selectbox(key="cmp_site_2").set_value("artemis_nobile_rim_2").run()
    assert not at.exception, [e.message for e in at.exception]


def test_url_reproduces_the_scenario_and_expert_mode():
    at = _run(APP / "pages" / "site.py", site="change_7_target", t="2027-03-01T06:00Z", days="7", mast="10",
              mode="expert")
    assert not at.exception
    assert at.session_state["site"] == "change_7_target" and at.session_state["days"] == 7
    assert at.query_params["mast"] in ("10", ["10"]) and len(at.metric) >= 6


def test_custom_site_is_labelled_coarser():
    at = _run(APP / "pages" / "site.py", site="custom", lat="-89.45", lon="-137.3")
    assert not at.exception
    assert any("Coarser terrain (160 m)" in m.value for m in [*at.markdown, *at.caption])
