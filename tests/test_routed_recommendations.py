from dataclasses import replace

from fastapi.testclient import TestClient

from app.data_store import DataStore
from app.main import create_app
from app.retrieval import retrieve
from app.models import RecommendRequest
from app.walking import WalkingLeg


class DetourNetwork:
    def route(self, start, end):
        return WalkingLeg(2000, [[start[1], start[0]], [end[1], end[0]]], 0)


class DisconnectedNetwork:
    def route(self, start, end):
        return None


def test_real_path_detour_overrides_optimistic_straight_line(settings, payload):
    request = RecommendRequest(**(payload | {'available_minutes': 20}))
    dataset = DataStore(settings.data_dir).get()
    assert retrieve(request, dataset).candidates
    assert not retrieve(request, dataset, DetourNetwork()).candidates


def test_missing_path_is_not_fabricated(settings, payload):
    result = retrieve(RecommendRequest(**payload), DataStore(settings.data_dir).get(), DisconnectedNetwork())
    assert not result.candidates
    assert 'связного пути' in result.message


def test_missing_graph_is_explicit_heuristic(settings, payload):
    settings = replace(settings, walking_dir=settings.data_dir / 'missing-walk')
    with TestClient(create_app(settings)) as client:
        response = client.post('/api/recommend', json=payload)
        assert response.status_code == 200
        assert response.json()['recommendations']
        assert all(p['travel_basis'] == 'straight_line_estimate' and p['route_distance_m'] is None
                   for p in response.json()['recommendations'])
        plan = client.post('/api/itinerary', json={k: v for k, v in payload.items() if k != 'category'})
        assert plan.status_code == 200
        assert plan.json()['status'] == 'network_unavailable'
        assert not plan.json()['legs']


def test_itinerary_validation_omits_sensitive_input(client):
    response = client.post('/api/itinerary', json={'lat': 100, 'lon': 71, 'available_minutes': 60})
    assert response.status_code == 422
    assert all('input' not in e for e in response.json()['detail'])
