import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_locations_contract(client):
    response = client.get("/api/locations")
    assert response.status_code == 200
    for location in response.json()["locations"]:
        assert set(location) == {"id", "name", "lat", "lon"}


def test_walk_has_real_source_and_honest_fallback(client, payload):
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"mode", "used_context", "recommendations", "message"}
    assert body["mode"] == "fallback"
    assert body["used_context"] == {k: v for k, v in payload.items() if k != "query"}
    assert 1 <= len(body["recommendations"]) <= 3
    for row in body["recommendations"]:
        assert row["poi_id"] in {"osm_node_1", "osm_node_2"}
        assert row["source_url"].startswith("https://www.openstreetmap.org/")
        assert row["total_minutes_estimate"] == 2 * row["walk_minutes_estimate"] + row["visit_minutes_estimate"]
        assert row["total_minutes_estimate"] <= payload["available_minutes"]
        assert row["distance_kind"] == "straight_line"
        assert any("Часы работы не подтверждены" in w for w in row["warnings"])
    assert response.headers["cache-control"] == "no-store"


def test_twenty_minutes_changes_eligible_set(client, payload):
    sixty = client.post("/api/recommend", json=payload).json()["recommendations"]
    twenty = client.post("/api/recommend", json=payload | {"available_minutes": 20}).json()["recommendations"]
    assert {p["poi_id"] for p in twenty} < {p["poi_id"] for p in sixty}
    assert all(p["total_minutes_estimate"] <= 20 for p in twenty)


def test_coffee_only(client, payload):
    body = client.post("/api/recommend", json=payload | {"category": "cafe", "query": "Кофе рядом"}).json()
    assert body["recommendations"]
    assert all(row["category"] == "cafe" for row in body["recommendations"])


@pytest.mark.parametrize("query", ["Кофе с розеткой", "Тихое кафе", "Нужно тихое место с кофе и розеткой"])
def test_unconfirmed_features_do_not_match(client, payload, query):
    body = client.post("/api/recommend", json=payload | {"category": "cafe", "query": query}).json()
    assert body["recommendations"] == []
    assert "Не подтверждены" in body["message"]


def test_confirmed_wifi_can_match(client, payload):
    body = client.post("/api/recommend", json=payload | {"category": "cafe", "query": "Кафе с Wi-Fi"}).json()
    assert [p["poi_id"] for p in body["recommendations"]] == ["osm_node_4"]
    assert "Wi-Fi" in body["recommendations"][0]["why"]
    assert any("доступность сейчас не подтверждены" in w for w in body["recommendations"][0]["warnings"])


def test_no_match_and_no_silent_category_change(client, payload):
    body = client.post("/api/recommend", json=payload | {"query": "Хочу музей"}).json()
    assert body["recommendations"] == []
    conflicting = client.post("/api/recommend", json=payload | {"query": "Хочу кофе"}).json()
    assert conflicting["recommendations"] == []
    assert "расходятся" in conflicting["message"]


@pytest.mark.parametrize("query", ["Кафе открыто сейчас", "Ищу ночную активность", "2 часа до вылета", "Бесплатный музей", "Музей с интерактивами"])
def test_unsupported_constraints_are_explicit(client, payload, query):
    body = client.post("/api/recommend", json=payload | {"query": query}).json()
    assert body["recommendations"] == []
    assert body["message"]


def test_outside_coverage(client, payload):
    body = client.post("/api/recommend", json=payload | {"lat": 43.2, "lon": 76.9}).json()
    assert body["recommendations"] == []
    assert "зоне покрытия" in body["message"]


@pytest.mark.parametrize("change", [
    {"lat": 91}, {"lon": -181}, {"available_minutes": 9}, {"available_minutes": 181},
    {"available_minutes": 20.5}, {"available_minutes": True}, {"category": "night"},
    {"query": " "}, {"query": "a" * 1001}, {"extra": "not allowed"},
])
def test_input_validation(client, payload, change):
    response = client.post("/api/recommend", json=payload | change)
    assert response.status_code == 422
    assert all("input" not in error for error in response.json()["detail"])


def test_missing_frontend_does_not_break_api_and_can_be_added(client, settings):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 404
    settings.static_dir.mkdir()
    (settings.static_dir / "index.html").write_text("<!doctype html><title>integration test</title>", encoding="utf-8")
    (settings.static_dir / "app.js").write_text("console.log('test');", encoding="utf-8")
    assert "integration test" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/locations").status_code == 200


def test_missing_dataset_returns_503(tmp_path, payload):
    with TestClient(create_app(Settings(data_dir=tmp_path / "absent", static_dir=tmp_path / "none"))) as client:
        assert client.get("/api/health").status_code == 503
        response = client.post("/api/recommend", json=payload)
        assert response.status_code == 503
        assert "collect_pois.py" in response.json()["detail"]


def test_api_does_not_write_user_data(client, settings, payload):
    before = {str(p): p.read_bytes() for p in settings.data_dir.rglob("*") if p.is_file()}
    client.post("/api/recommend", json=payload | {"query": "Хочу погулять private-user-token"})
    after = {str(p): p.read_bytes() for p in settings.data_dir.rglob("*") if p.is_file()}
    assert before == after


def test_meta_explains_source_and_limits(client):
    meta = client.get("/api/meta").json()
    assert meta["poi_count"] == 4
    assert meta["license"] == "ODbL 1.0"
    assert "BM25" in meta["retrieval"]
    assert meta["limitations"]
