"""Audit the actual dataset distributed in the repository, without network access."""
import hashlib
import json

from app.config import ROOT
from app.data_store import DataStore
from scripts.collect_pois import normalize


def snapshot():
    root = ROOT / "data"
    folder = root / json.loads((root / "current.json").read_text(encoding="utf-8"))["snapshot"]
    raw = json.loads((folder / "raw.json").read_text(encoding="utf-8"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    return folder, raw, manifest


def test_shipped_raw_response_matches_manifest_hash():
    folder, raw, manifest = snapshot()
    assert hashlib.sha256((folder / "raw.json").read_bytes()).hexdigest() == manifest["raw_sha256"]
    assert len(raw["elements"]) == manifest["raw_elements"]
    assert raw["osm3s"]["timestamp_osm_base"] == manifest["source_data_timestamp"]


def test_all_shipped_processed_snapshots_match_manifest_hashes():
    """Protect amenities/hours as well as source IDs, including archived snapshots."""
    for folder in (ROOT / "data" / "snapshots").iterdir():
        if not folder.is_dir():
            continue
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        for name in ("pois", "locations"):
            content = (folder / f"{name}.json").read_bytes()
            assert b"\r\n" not in content
            assert hashlib.sha256(content).hexdigest() == manifest[f"{name}_sha256"]


def test_shipped_records_are_reproducible_from_raw_source():
    folder, raw, manifest = snapshot()
    pois, locations, skipped = normalize(raw, manifest["collected_at"])
    assert pois == json.loads((folder / "pois.json").read_text(encoding="utf-8"))
    assert locations == json.loads((folder / "locations.json").read_text(encoding="utf-8"))
    assert skipped == manifest["skipped"]


def test_every_shipped_poi_and_starting_location_has_an_osm_source():
    folder, raw, manifest = snapshot()
    raw_ids = {f"osm_{e['type']}_{e['id']}" for e in raw["elements"]}
    dataset = DataStore(ROOT / "data").get()
    assert len(dataset.pois) == manifest["poi_count"]
    assert all(p.poi_id in raw_ids for p in dataset.pois)
    assert all(l.id in raw_ids for l in dataset.locations)
