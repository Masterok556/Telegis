"""Cross-endpoint climate contracts and honest graph geometry."""
from dataclasses import replace
from datetime import datetime, timezone
from math import ceil

from fastapi.testclient import TestClient
import pytest

from app.climate import climate_context, indoor_evidence
from app.geo import distance_m
from app.main import create_app
from app.weather import WeatherCurrent, WeatherSnapshot, climate_policy, demo_snapshot
from app.walking import WalkingNetwork


def snapshot(status="live", apparent=10):
    current = WeatherCurrent(
        temperature_c=apparent, apparent_temperature_c=apparent,
        wind_m_s=2, gust_m_s=3, precipitation_mm=0,
        precipitation_interval_seconds=900, weather_code=2, is_day=True,
    )
    now = datetime.now(timezone.utc)
    return WeatherSnapshot(
        status=status, source="Open-Meteo", source_url="https://open-meteo.com/en/docs",
        valid_at=now, fetched_at=now, age_seconds=0,
        current=current if status != "unavailable" else None,
        policy=climate_policy(current), attribution="Synthetic test fixture",
    )


class WeatherStub:
    def __init__(self, value):
        self.value = value
        self.calls = []

    async def get(self, demo=False):
        self.calls.append(demo)
        return demo_snapshot() if demo else self.value


def make_client(settings, weather, monkeypatch, *, indoors=False, graph=False):
    app = create_app(settings, weather_service=weather)
    dataset = app.state.store.get()
    if indoors:
        # Just one explicit indoor tag. A cafe/category or an advertising name is insufficient.
        pois = tuple(p.model_copy(update={"tags": p.tags | {"indoor_seating": "yes"}})
                     if p.poi_id == "osm_node_3" else
                     p.model_copy(update={"name": "MEGA AITU HUB indoor"}) if p.poi_id == "osm_node_4" else p
                     for p in dataset.pois)
        dataset = replace(dataset, pois=pois)
        monkeypatch.setattr(app.state.store, "get", lambda: dataset)
    if graph:
        nodes = {i: (p.lat, p.lon) for i, p in enumerate(dataset.pois, 1)}
        edges = [(a, b, distance_m(*nodes[a], *nodes[b])) for a in nodes for b in nodes if a != b]
        network = WalkingNetwork(nodes, edges, {"snapshot_id": "synthetic-test"})
    else:
        network = None
    monkeypatch.setattr("app.main.walking_network", lambda root: network)
    return TestClient(app), dataset, network


def test_disabled_climate_does_not_contact_weather(settings, payload, monkeypatch):
    weather = WeatherStub(snapshot())
    client, _, _ = make_client(settings, weather, monkeypatch)
    with client:
        body = client.post("/api/recommend", json=payload).json()
    assert body["recommendations"] and not weather.calls
    assert body["used_context"]["climate"]["policy"] == "off"


def test_current_normal_weather_preserves_relevant_results(settings, payload, monkeypatch):
    weather = WeatherStub(snapshot())
    client, _, _ = make_client(settings, weather, monkeypatch)
    with client:
        ordinary = client.post("/api/recommend", json=payload).json()
        enabled = client.post("/api/recommend", json=payload | {"climate_shield": True}).json()
    assert [p["poi_id"] for p in ordinary["recommendations"]] == [p["poi_id"] for p in enabled["recommendations"]]
    context = enabled["used_context"]["climate"]
    assert context["applied"] and context["policy"] == "normal"
    assert context["weather"]["status"] == "live"
    assert weather.calls == [False]


def test_cold_weather_only_explicit_indoor_evidence(settings, payload, monkeypatch):
    weather = WeatherStub(snapshot(apparent=-15))
    client, dataset, _ = make_client(settings, weather, monkeypatch, indoors=True)
    with client:
        body = client.post("/api/recommend", json=payload | {
            "query": "Кофе", "category": "cafe", "climate_shield": True,
        }).json()
    assert body["used_context"]["climate"]["policy"] == "indoor_only"
    assert [p["poi_id"] for p in body["recommendations"]] == ["osm_node_3"]
    result = body["recommendations"][0]
    assert result["climate_shielded"]
    assert result["indoor_evidence"][0]["id"] == "osm_indoor_seating"
    assert result["indoor_evidence"][0]["source_url"].endswith("/node/3")
    assert any("Переходы" in warning for warning in result["warnings"])
    assert not indoor_evidence(next(p for p in dataset.pois if p.poi_id == "osm_node_4"))


@pytest.mark.parametrize("status,apparent", [
    ("stale", -15), ("unavailable", 10), ("demo", -15), ("live", -25),
])
def test_uncertain_or_extreme_weather_does_not_make_a_route(settings, payload, monkeypatch, status, apparent):
    weather = WeatherStub(snapshot(status, apparent))
    client, _, _ = make_client(settings, weather, monkeypatch, indoors=True, graph=True)
    with client:
        recommendation = client.post("/api/recommend", json=payload | {"climate_shield": True}).json()
        itinerary = client.post("/api/itinerary", json={k: v for k, v in payload.items() if k != "category"} |
                                {"climate_shield": True}).json()
        route = client.post("/api/route", json={"lat": payload["lat"], "lon": payload["lon"],
                                              "poi_id": "osm_node_3", "climate_shield": True}).json()
    assert recommendation["recommendations"] == []
    assert itinerary["status"] == route["status"] == "no_match"
    assert itinerary["stops"] == route["coordinates"] == []
    assert all(item["used_context"]["climate"]["policy"] == "paused" for item in (recommendation, itinerary, route))


def test_demo_endpoint_is_marked_and_never_changes_real_climate(settings, payload, monkeypatch):
    weather = WeatherStub(snapshot(apparent=10))
    client, _, _ = make_client(settings, weather, monkeypatch)
    with client:
        assert client.get("/api/weather?demo=true").json()["status"] == "demo"
        real = client.post("/api/recommend", json=payload | {"climate_shield": True}).json()
    assert real["used_context"]["climate"]["policy"] == "normal"
    assert real["used_context"]["climate"]["weather"]["status"] == "live"
    assert weather.calls == [True, False]


@pytest.mark.parametrize("endpoint", ["/api/recommend", "/api/itinerary", "/api/route"])
@pytest.mark.parametrize("change", [{"climate_shield": "false"}, {"climate_shield": 1},
                                   {"weather": {"temperature_c": 15}}, {"demo": True}, {"locale": "fr"}])
def test_client_cannot_override_weather_or_weaken_validation(client, payload, endpoint, change):
    body = payload if endpoint.endswith("recommend") else {k: v for k, v in payload.items() if k != "category"}
    if endpoint.endswith("route"):
        body = {"lat": payload["lat"], "lon": payload["lon"], "poi_id": "osm_node_3"}
    response = client.post(endpoint, json=body | change)
    assert response.status_code == 422
    assert all("input" not in error for error in response.json()["detail"])


def test_indoor_no_overrides_seating_yes(settings):
    poi = create_app(settings).state.store.get().pois[0]
    assert indoor_evidence(poi.model_copy(update={"tags": {"indoor": "no", "indoor_seating": "yes"}})) == []
    assert indoor_evidence(poi.model_copy(update={"tags": {"description": "indoor", "name": "MEGA"}})) == []


def test_itinerary_accepts_climate_and_normal_mode_keeps_return_budget(settings, payload, monkeypatch):
    weather = WeatherStub(snapshot())
    client, _, _ = make_client(settings, weather, monkeypatch, graph=True)
    with client:
        response = client.post("/api/itinerary", json={
            "lat": payload["lat"], "lon": payload["lon"], "available_minutes": 120,
            "query": "Прогулка и кофе", "include_coffee": True, "climate_shield": True,
        })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "ready"
    assert result["route_coordinates"][0] == result["route_coordinates"][-1]
    assert result["legs"][-1]["to_id"] == "start"
    assert result["total_minutes_estimate"] == (
        sum(leg["walk_minutes_estimate"] for leg in result["legs"])
        + sum(stop["visit_minutes_estimate"] for stop in result["stops"])
        + result["reserve_minutes"])
    assert result["total_minutes_estimate"] <= 120


def test_cold_itinerary_cannot_silently_add_outdoor_stops(settings, payload, monkeypatch):
    weather = WeatherStub(snapshot(apparent=-15))
    client, _, _ = make_client(settings, weather, monkeypatch, indoors=True, graph=True)
    with client:
        response = client.post("/api/itinerary", json={
            "lat": payload["lat"], "lon": payload["lon"], "available_minutes": 120,
            "climate_shield": True,
        })
    assert response.status_code == 200
    assert response.json()["status"] == "no_match"
    assert not response.json()["route_coordinates"]


def test_single_destination_uses_graph_and_labels_one_way(settings, payload, monkeypatch):
    weather = WeatherStub(snapshot())
    client, dataset, network = make_client(settings, weather, monkeypatch, graph=True)
    poi = next(p for p in dataset.pois if p.poi_id == "osm_node_3")
    expected = network.route((payload["lat"], payload["lon"]), (poi.lat, poi.lon))
    with client:
        body = client.post("/api/route", json={"lat": payload["lat"], "lon": payload["lon"],
                                              "poi_id": poi.poi_id}).json()
    assert body["status"] == "ready"
    assert body["coordinates"] == expected.coordinates
    assert body["distance_m"] == expected.distance_m
    assert body["walk_minutes_estimate"] == max(1, ceil(expected.distance_m / 70))
    assert body["used_context"]["return_to_start"] is False
    assert any("одну сторону" in w for w in body["warnings"])
    assert not weather.calls


def test_single_destination_no_graph_never_draws_direct_line(settings, payload, monkeypatch):
    client, _, _ = make_client(settings, WeatherStub(snapshot()), monkeypatch)
    with client:
        body = client.post("/api/route", json={"lat": payload["lat"], "lon": payload["lon"],
                                              "poi_id": "osm_node_3"}).json()
    assert body["status"] == "network_unavailable" and not body["coordinates"]
    assert body["walk_minutes_estimate"] == 0


def test_single_destination_unknown_and_outside_coverage(settings, payload, monkeypatch):
    client, _, _ = make_client(settings, WeatherStub(snapshot()), monkeypatch, graph=True)
    with client:
        for data in ({"lat": payload["lat"], "lon": payload["lon"], "poi_id": "osm_node_9999"},
                     {"lat": 43.2, "lon": 76.9, "poi_id": "osm_node_3"}):
            body = client.post("/api/route", json=data).json()
            assert body["status"] == "no_match" and not body["coordinates"]
