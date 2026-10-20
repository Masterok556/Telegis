"""Regression tests for the merged UI/API and the former preview file server."""
import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data_store import DataStore, DatasetUnavailable
from app.main import create_app


def test_catalog_and_drawer_share_validated_data(client):
    catalog = client.get("/api/pois")
    assert catalog.status_code == 200
    cards = catalog.json()["pois"]
    assert len(cards) == 4
    for card in cards:
        assert card["confirmed_features"]["socket"] is None
        assert card["confirmed_features"]["quiet"] is None
        assert card["warnings"]
        info = client.post("/api/poi_ai_info", json={"poi_id": card["poi_id"]})
        assert info.status_code == 200
        body = info.json()
        assert body["mode"] == "sourced"
        assert body["summary"] == card["description"]
        assert body["evidence"] == card["evidence"]
        assert body["activity_source"] == "suggested_idea"
        assert body["tip"]
        assert body["source_url"] == card["source_url"]
    assert catalog.headers["cache-control"] == "no-store"


def test_drawer_never_uses_client_invented_places_or_facts(client):
    assert client.post("/api/poi_ai_info", json={"poi_id": "osm_node_9999999"}).status_code == 404
    assert client.post("/api/poi_ai_info", json={"poi_id": "osm_node_fake"}).status_code == 422
    assert client.post("/api/poi_ai_info", json={
        "poi_id": "osm_node_1", "name": "Invented", "opening_hours": "24/7",
    }).status_code == 422


@pytest.mark.parametrize("path", [
    "/.env", "/env.txt", "/app/config.py", "/.git/config",
    "/static/../.env", "/static/%2e%2e/.env",
    "/presentation/%2e%2e/.env", "/static/%2e%2e%5c.env",
])
def test_repository_secrets_are_not_web_assets(tmp_path, path):
    # Sentinel only: never read or transmit the real .env in a security test.
    (tmp_path / ".env").write_text("LLM_API_KEY=SECRET-SENTINEL", encoding="utf-8")
    (tmp_path / "static").mkdir()
    (tmp_path / "presentation").mkdir()
    with TestClient(create_app(Settings(static_dir=tmp_path / "static"))) as client:
        response = client.get(path)
    assert response.status_code == 404
    assert "SECRET-SENTINEL" not in response.text


def test_in_place_snapshot_corruption_cannot_hide_behind_cache(settings):
    store = DataStore(settings.data_dir)
    dataset = store.get()
    folder = settings.data_dir / "snapshots" / dataset.manifest["snapshot_id"]
    path = folder / "pois.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows.append(rows[0])
    path.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(DatasetUnavailable):
        store.get()


@pytest.mark.parametrize("change", [
    lambda row: row["confirmed_features"].update(socket=True),
    lambda row: row.update(opening_hours="24/7"),
])
def test_unsupported_facts_with_same_ids_and_counts_are_rejected(settings, change):
    store = DataStore(settings.data_dir)
    dataset = store.get()
    folder = settings.data_dir / "snapshots" / dataset.manifest["snapshot_id"]
    path = folder / "pois.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    change(rows[0])
    path.write_bytes((json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    for reader in (store, DataStore(settings.data_dir)):
        with pytest.raises(DatasetUnavailable):
            reader.get()


def test_metadata_reports_real_model_readiness(client):
    meta = client.get("/api/meta").json()
    assert meta["llm_configured"] is False
    assert meta["llm_model"] is None
    assert meta["llm_last_status"] == "not_configured"
    assert meta["data_quality"]["confirmed_features"]["socket"] == 0


def test_map_document_sends_origin_but_api_keeps_private_referrer_policy(client):
    assert client.get("/").headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert client.get("/api/pois").headers["referrer-policy"] == "no-referrer"


def test_local_map_contains_only_actual_graph_edges(client, monkeypatch):
    from app import main
    from app.geo import distance_m
    from app.walking import WalkingNetwork
    nodes = {1: (51.09, 71.40), 2: (51.091, 71.40), 3: (51.092, 71.401)}
    edges = [(a, b, distance_m(*nodes[a], *nodes[b])) for a, b in [(1, 2), (2, 1), (2, 3)]]
    network = WalkingNetwork(nodes, edges, {"snapshot_id": "test-public-graph"})
    monkeypatch.setattr(main, "walking_network", lambda root: network)
    result = client.get("/api/walking-map.geojson")
    assert result.status_code == 200
    body = result.json()
    assert body["snapshot_id"] == "test-public-graph"
    assert body["license"] == "ODbL 1.0"
    assert body["features"][0]["geometry"] == {
        "type": "MultiLineString",
        "coordinates": [[[71.40, 51.09], [71.40, 51.091]], [[71.40, 51.091], [71.401, 51.092]]],
    }


def test_missing_local_graph_returns_explicit_failure(client):
    assert client.get("/api/walking-map.geojson").status_code == 503
