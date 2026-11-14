"""pipeline/sites.py: the catalog and lander presets load, are complete, and reject bad entries."""

import pytest
import yaml

from pipeline import sites as S

REQUIRED = {
    "artemis_peak_near_cabeus_b", "artemis_haworth", "artemis_malapert_massif", "artemis_mons_mouton_plateau",
    "artemis_mons_mouton", "artemis_nobile_rim_1", "artemis_nobile_rim_2", "artemis_de_gerlache_rim_2",
    "artemis_slater_plain", "im2_target", "im2_actual", "im1_odysseus", "chandrayaan_3", "blue_ghost_1",
    "blue_moon_mk1_target", "change_7_target", "apollo_11",
}


def test_catalog_has_every_required_site():
    assert {s["id"] for s in S.load_sites()} == REQUIRED


def test_artemis_regions_are_labelled_approximate_and_polar():
    for s in S.load_sites():
        if s["group"] == "artemis_region":
            assert "approximate" in s["note"].lower() and s["in_polar_dem"]


def test_athena_has_landing_time_and_target():
    athena = S.site_by_id("im2_actual")
    assert athena["landing_utc"].startswith("2025-03-06T17:28") and athena["target"] == {"lat": -84.78, "lon": 29.13}


def test_every_lander_number_is_cited_or_illustrative():
    for lander in S.load_landers().values():
        for field in S.LANDER_NUMBERS:
            src = lander["sources"][field]
            assert src == S.ILLUSTRATIVE or "https://" in src


@pytest.mark.parametrize("change, message", [
    ({"lat": -95}, "lat"), ({"lon": 180}, "lon"), ({"group": "rover"}, "group"),
    ({"source_url": "lroc.asu.edu"}, "https"), ({"id": "Bad Id"}, "slug"), ({"landing_utc": "2025-03-06 17:28"}, "Z"),
])
def test_bad_site_is_rejected(tmp_path, change, message):
    site = {"id": "x", "name": "X", "group": "clps", "lat": -85.0, "lon": 10.0,
            "source_url": "https://example.org", "note": "n"} | change
    path = tmp_path / "sites.yaml"
    path.write_text(yaml.safe_dump({"sites": [site]}))
    with pytest.raises(ValueError, match=message):
        S.load_sites(path)


def test_uncited_lander_number_is_rejected(tmp_path):
    landers = yaml.safe_load((S.HERE / "landers.yaml").read_text())
    landers["landers"]["nova_c"]["sources"]["array_W"] = "I think so"
    path = tmp_path / "landers.yaml"
    path.write_text(yaml.safe_dump(landers))
    with pytest.raises(ValueError, match="array_W"):
        S.load_landers(path)
