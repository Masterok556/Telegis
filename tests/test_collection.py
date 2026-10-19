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
