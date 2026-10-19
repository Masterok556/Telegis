"""Source integrity and failed-publication regressions, using temporary test data."""
import json

import pytest

from app.data_store import DataStore, DatasetUnavailable
from scripts import collect_pois


def snapshot_folder(settings):
    pointer = json.loads((settings.data_dir / "current.json").read_text(encoding="utf-8"))
    return settings.data_dir / pointer["snapshot"]


@pytest.mark.parametrize("filename,change", [
    ("manifest.json", lambda value: value.pop("coverage")),
    ("manifest.json", lambda value: value.update(categories={"museum": value["poi_count"]})),
    ("manifest.json", lambda value: value.update(locations_count=999)),
    ("manifest.json", lambda value: value.update(collected_at="2026-10-19T00:00:00")),
    ("locations.json", lambda value: value[0].update(lat=value[0]["lat"] + 0.1)),
    ("pois.json", lambda value: value[0].update(source_url="https://www.openstreetmap.org/node/99999")),
    ("raw.json", lambda value: value.update(generator="Changed source after collection")),
])
def test_corrupted_snapshot_is_unavailable_instead_of_serving_false_facts(settings, filename, change):
    target = snapshot_folder(settings) / filename
    value = json.loads(target.read_text(encoding="utf-8"))
    change(value)
    target.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(DatasetUnavailable):
        DataStore(settings.data_dir).get()


def test_invalid_export_never_replaces_last_working_dataset(settings, raw_fixture):
    pointer = settings.data_dir / "current.json"
    before = pointer.read_bytes()
    with pytest.raises(ValueError):
        collect_pois.publish(raw_fixture, settings.data_dir, "test", "test", "missing-timezone")
    assert pointer.read_bytes() == before
    assert len(DataStore(settings.data_dir).get().pois) == 4


def test_partial_write_never_replaces_last_working_dataset(settings, raw_fixture, monkeypatch):
    pointer = settings.data_dir / "current.json"
    before = pointer.read_bytes()
    original_write = collect_pois.write_json

    def fail_manifest_write(path, value):
        if path.name == "manifest.json":
            raise OSError("Simulated disk write failure")
        return original_write(path, value)

    monkeypatch.setattr(collect_pois, "write_json", fail_manifest_write)
    with pytest.raises(OSError):
        collect_pois.publish(raw_fixture, settings.data_dir, "test", "test", "2026-10-19T00:00:00+00:00")
    assert pointer.read_bytes() == before
    assert len(DataStore(settings.data_dir).get().pois) == 4
