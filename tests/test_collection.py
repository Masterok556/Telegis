from datetime import datetime, timezone
import json

import pytest

from app.data_store import DataStore, DatasetUnavailable
from scripts.collect_pois import normalize, publish


def test_normalization_deduplicates_and_keeps_unknown_unknown(raw_fixture):
    raw_fixture["elements"].append(raw_fixture["elements"][0].copy())
    pois, locations, skipped = normalize(raw_fixture, datetime.now(timezone.utc).isoformat())
    assert len(pois) == 4
    assert skipped["duplicate_id"] == 1
    assert skipped["restricted_access"] == 1
    coffee = next(p for p in pois if p["poi_id"] == "osm_node_3")
    assert coffee["confirmed_features"]["socket"] is None
    assert coffee["rating"] is None
    assert coffee["opening_hours"] is None
    assert all(l["id"] in {p["poi_id"] for p in pois} for l in locations)


def test_failed_update_preserves_last_good_snapshot(settings):
    old = (settings.data_dir / "current.json").read_bytes()
    with pytest.raises(ValueError):
        publish({"elements": [], "remark": "timeout"}, settings.data_dir, "test", "test", datetime.now(timezone.utc).isoformat())
    assert (settings.data_dir / "current.json").read_bytes() == old
    assert len(DataStore(settings.data_dir).get().pois) == 4


def test_snapshot_change_reload_without_restart(settings, raw_fixture):
    store = DataStore(settings.data_dir)
    assert len(store.get().pois) == 4
    raw_fixture["elements"] = raw_fixture["elements"][:2]
    publish(raw_fixture, settings.data_dir, "test", "test", datetime.now(timezone.utc).isoformat())
    assert len(store.get().pois) == 2


def test_snapshot_path_traversal_is_rejected(settings):
    (settings.data_dir / "current.json").write_text(json.dumps({"snapshot": "../../outside"}), encoding="utf-8")
    with pytest.raises(DatasetUnavailable):
        DataStore(settings.data_dir).get()


def test_unnamed_playground_uses_an_explicit_descriptive_label(raw_fixture):
    raw_fixture["elements"].append({
        "type": "node", "id": 88, "lat": 51.090, "lon": 71.419,
        "tags": {"leisure": "playground", "surface": "rubber", "lit": "yes"},
    })
    pois, _, _ = normalize(raw_fixture, "2026-10-19T00:00:00+00:00")
    place = next(p for p in pois if p["poi_id"] == "osm_node_88")
    assert place["name_kind"] == "descriptive"
    assert "без названия" in place["name"] and "88" in place["name"]
    assert "не официальное название" in place["description"]
    assert "возраст не подтверждены" in place["description"]
    assert "name" not in place["tags"]
    assert place["tags"]["surface"] == "rubber"
    assert place["tags"]["lit"] == "yes"
    assert place["opening_hours"] is None
    assert all(value is None for value in place["confirmed_features"].values())


@pytest.mark.parametrize("extra_tags", [
    {"access": "private"}, {"access": "no"}, {"access": "customers"},
    {"access": "permit"}, {"access": "members"}, {"indoor": "yes"},
    {"access:conditional": "yes @ (Mo-Fr 10:00-17:00)"},
])
def test_unnamed_playground_with_unverified_access_is_not_published(raw_fixture, extra_tags):
    raw_fixture["elements"].append({
        "type": "node", "id": 88, "lat": 51.090, "lon": 71.419,
        "tags": {"leisure": "playground"} | extra_tags,
    })
    pois, _, _ = normalize(raw_fixture, "2026-10-19T00:00:00+00:00")
    assert "osm_node_88" not in {p["poi_id"] for p in pois}


def test_nearby_unnamed_node_and_area_are_not_duplicate_recommendations(raw_fixture):
    raw_fixture["elements"] += [
        {"type": "node", "id": 88, "lat": 51.090, "lon": 71.419,
         "tags": {"leisure": "playground"}},
        {"type": "way", "id": 89, "center": {"lat": 51.09001, "lon": 71.419},
         "tags": {"leisure": "playground", "surface": "rubber"}},
    ]
    pois, _, skipped = normalize(raw_fixture, "2026-10-19T00:00:00+00:00")
    playgrounds = [p for p in pois if p["category"] == "playground"]
    assert len(playgrounds) == 1
    assert playgrounds[0]["poi_id"] == "osm_way_89"
    assert skipped["duplicate_name_nearby"] == 1


def test_unnamed_cafe_is_still_not_invented(raw_fixture):
    raw_fixture["elements"].append({
        "type": "node", "id": 88, "lat": 51.090, "lon": 71.419,
        "tags": {"amenity": "cafe"},
    })
    pois, _, _ = normalize(raw_fixture, "2026-10-19T00:00:00+00:00")
    assert "osm_node_88" not in {p["poi_id"] for p in pois}
