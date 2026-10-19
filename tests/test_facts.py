from copy import deepcopy
import json

import pytest

from app.facts import excluded_from_routes, facts_for, warnings_for
from app.models import POI
from scripts.enrich_pois import SOURCES, extract_record, publish, validate_url


def make_poi(**kwargs):
    base = {"poi_id": "osm_node_1", "name": "Test coffee", "lat": 51.09, "lon": 71.41,
            "category": "cafe", "description": "test", "tags": {}, "opening_hours": None,
            "source_url": "https://www.openstreetmap.org/node/1",
            "collected_at": "2026-10-19T00:00:00+00:00", "coordinate_kind": "point",
            "confirmed_features": {"quiet": None, "socket": None, "wifi": None, "wheelchair": None}}
    return POI.model_validate(base | kwargs)


def test_no_amenities_invented_from_category_or_name(tmp_path):
    assert facts_for(make_poi(name="Quiet WiFi cafe with sockets"), tmp_path) == []


def test_source_tag_translations_are_attributable_and_not_live(tmp_path):
    poi = make_poi(tags={"cuisine": "coffee_shop;breakfast;unknown", "internet_access": "wlan",
                         "outdoor_seating": "no", "addr:street": "Test street", "addr:housenumber": "10"})
    facts = facts_for(poi, tmp_path)
    assert [f["id"] for f in facts] == ["osm_cuisine", "osm_outdoor_seating", "osm_wifi", "osm_address"]
    assert "кофе, завтраки" in facts[0]["text"]
    assert all(f["source_url"] == poi.source_url and f["confidence"] == "source_reported" for f in facts)
    assert "нужно уточнить" in next(f["text"] for f in facts if f["id"] == "osm_wifi")


def test_generic_internet_is_not_claimed_wifi(tmp_path):
    facts = facts_for(make_poi(tags={"internet_access": "yes", "internet_access:fee": "no"}), tmp_path)
    assert "osm_wifi" not in {f["id"] for f in facts}
    assert "способ подключения не уточнён" in facts[0]["text"]


def test_memorial_architecture_facts(tmp_path):
    facts = facts_for(make_poi(category="attraction", tags={"height": "20", "architect": "Name",
                     "start_date": "2011-12-16", "artwork_type": "sculpture"}), tmp_path)
    assert {f["id"] for f in facts} == {"osm_height", "osm_architect", "osm_start_date", "osm_artwork_type"}


def record_for(poi):
    return {"identity": {"name": poi.name, "lat": poi.lat, "lon": poi.lon, "source_url": poi.source_url},
            "source_url": SOURCES[0]["url"], "collected_at": poi.collected_at, "published_at": "2019-07-09",
            "facts": [{"id": "detail", "text": "A test-only supported detail."}],
            "warnings": ["Historical source; current access unknown."], "exclude_from_routes": False}


def test_official_provenance_and_live_reload(tmp_path):
    poi = make_poi()
    record = record_for(poi)
    publish({poi.poi_id: record}, tmp_path)
    facts = facts_for(poi, tmp_path)
    assert facts[0]["kind"] == "official" and facts[0]["published_at"] == "2019-07-09"
    assert warnings_for(poi, tmp_path) == record["warnings"]
    record["facts"][0]["text"] = "New version test detail."
    publish({poi.poi_id: record}, tmp_path)
    assert facts_for(poi, tmp_path)[0]["text"] == "New version test detail."


@pytest.mark.parametrize("field,value", [("name", "Another venue"), ("lat", 51.5), ("source_url", "https://www.openstreetmap.org/node/999")])
def test_official_data_not_attached_to_wrong_identity(tmp_path, field, value):
    poi = make_poi()
    record = record_for(poi)
    record["identity"][field] = value
    publish({poi.poi_id: record}, tmp_path)
    assert facts_for(poi, tmp_path) == []


def test_invalid_official_url_or_corrupt_file_does_not_break_osm(tmp_path):
    poi = make_poi(tags={"cuisine": "coffee_shop"})
    record = record_for(poi)
    record["source_url"] = "https://example.org/forged"
    publish({poi.poi_id: record}, tmp_path)
    assert [f["kind"] for f in facts_for(poi, tmp_path)] == ["osm_tag"]
    pointer = json.loads((tmp_path / "current.json").read_text())
    (tmp_path / pointer["snapshot"] / "records.json").write_text("tampered", encoding="utf-8")
    assert [f["kind"] for f in facts_for(poi, tmp_path)] == ["osm_tag"]


def test_project_hold_survives_missing_optional_data(tmp_path):
    poi = make_poi(poi_id="osm_way_1467797207", source_url="https://www.openstreetmap.org/way/1467797207", name="NU Park")
    assert excluded_from_routes(poi, tmp_path)
    assert "будущий проект" in warnings_for(poi, tmp_path)[0]
    assert not excluded_from_routes(make_poi(), tmp_path)


def test_extraction_requires_each_supporting_phrase():
    source = deepcopy(SOURCES[0])
    body = ("<article>" + " ".join(n for f in source["facts"] for n in f["needles"])
            + " " + " ".join(source["warning_needles"]) + "</article>").encode("utf-8")
    record = extract_record(source, body, make_poi(), "2026-10-19T00:00:00+00:00")
    assert len(record["facts"]) == 2 and len(record["body_sha256"]) == 64
    assert sum(len(s.split()) for s in record["supporting_excerpts"]) <= 25
    with pytest.raises(ValueError, match="Supporting phrase missing"):
        extract_record(source, b"<article>Page changed</article>", make_poi(), "2026-10-19T00:00:00+00:00")


def test_script_and_style_content_cannot_satisfy_evidence():
    source = deepcopy(SOURCES[2])
    text = " ".join(n for f in source["facts"] for n in f["needles"])
    with pytest.raises(ValueError, match="Supporting phrase missing"):
        extract_record(source, f"<script>{text}</script>".encode(), make_poi(), "2026-10-19T00:00:00+00:00")


@pytest.mark.parametrize("url", ["http://nu.edu.kz/path", "https://nu.edu.kz.evil.test/path", "https://user:password@nu.edu.kz/path", "https://127.0.0.1/", "https://nu.edu.kz:444/path"])
def test_fetch_url_allowlist_rejects_unknown_or_unsafe_redirects(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_shipped_optional_sources_have_valid_hashes():
    from app.data_store import DataStore
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    if not (root / "data" / "enrichment" / "current.json").exists():
        pytest.skip("Optional enrichment not yet collected")
    dataset = DataStore(root / "data").get()
    by_id = {p.poi_id: p for p in dataset.pois}
    for source in SOURCES:
        official = [f for f in facts_for(by_id[source["poi_id"]]) if f["kind"] == "official"]
        assert len(official) == len(source["facts"])
        assert all(f["source_url"] == source["url"] for f in official)
