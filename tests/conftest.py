"""Synthetic fixtures are test-only and never installed into the shipped dataset."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from scripts.collect_pois import CENTER, publish


@pytest.fixture
def raw_fixture():
    lat, lon = CENTER
    return {"osm3s": {"timestamp_osm_base": "2026-10-19T00:00:00Z"}, "elements": [
        {"type": "node", "id": 1, "lat": lat, "lon": lon,
         "tags": {"name": "Test art nearby", "tourism": "artwork"}},
        {"type": "node", "id": 2, "lat": lat + 0.006, "lon": lon,
         "tags": {"name": "Test park", "leisure": "park"}},
        {"type": "node", "id": 3, "lat": lat + 0.001, "lon": lon,
         "tags": {"name": "Test coffee", "amenity": "cafe"}},
        {"type": "node", "id": 4, "lat": lat + 0.003, "lon": lon,
         "tags": {"name": "Test WiFi coffee", "amenity": "cafe", "internet_access": "wlan", "opening_hours": "Mo-Su 09:00-21:00"}},
        {"type": "node", "id": 5, "lat": lat + 0.0001, "lon": lon,
         "tags": {"name": "Test private park", "leisure": "park", "access": "private"}},
    ]}


@pytest.fixture
def settings(tmp_path, raw_fixture):
    data_dir = tmp_path / "data"
    publish(raw_fixture, data_dir, "https://example.invalid/test-fixture", "TEST FIXTURE", datetime.now(timezone.utc).isoformat())
    return Settings(data_dir=data_dir, static_dir=tmp_path / "static")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def payload():
    return {"query": "Хочу погулять", "lat": CENTER[0], "lon": CENTER[1], "available_minutes": 60, "category": "walk"}
