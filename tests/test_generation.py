from dataclasses import replace
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.generation import Generator
from app.main import create_app


def mocked_client(settings, handler):
    configured = replace(settings, llm_api_key="TEST-KEY-NOT-A-SECRET", llm_model="test-model", llm_base_url="https://example.invalid/v1")
    return TestClient(create_app(configured, Generator(configured, transport=httpx.MockTransport(handler))))


def test_successful_grounded_rag_and_gps_not_sent(settings, payload):
    captured = []
    def handler(request):
        body = json.loads(request.content)
        captured.append(body)
        context = json.loads(body["messages"][1]["content"])
        c = context["candidates"][0]
        row = {"poi_id": c["poi_id"], "reason_ids": ["category", "budget"], "activity_id": next(iter(c["activities"]))}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"recommendations": [row]})}}]})
    with mocked_client(settings, handler) as client:
        body = client.post("/api/recommend", json=payload | {"query": "Хочу погулять secret-user-text 51.089 71.419"}).json()
    assert body["mode"] == "rag"
    assert len(body["recommendations"]) == 1
    outbound = json.dumps(captured)
    assert "secret-user-text" not in outbound
    assert "51.089" not in outbound and "71.419" not in outbound
    assert '"lat"' not in outbound and '"lon"' not in outbound


def test_unknown_id_and_extra_claims_rejected(settings, payload):
    def handler(request):
        content = {"recommendations": [
            {"poi_id": "invented_rooftop", "reason_ids": ["category"], "activity_id": "look_and_photo"},
            {"poi_id": "osm_node_1", "reason_ids": ["category"], "activity_id": "look_and_photo", "why": "Открыто сейчас, есть бесплатные билеты"},
        ]}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})
    with mocked_client(settings, handler) as client:
        body = client.post("/api/recommend", json=payload).json()
    assert body["mode"] == "fallback"
    assert "invented_rooftop" not in json.dumps(body)
    assert "бесплатные билеты" not in json.dumps(body, ensure_ascii=False)


def test_provider_error_is_fallback_and_not_exposed(settings, payload):
    def handler(request):
        return httpx.Response(401, text="TEST-KEY-NOT-A-SECRET private provider response")
    with mocked_client(settings, handler) as client:
        response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    assert response.json()["mode"] == "fallback"
    assert "TEST-KEY" not in response.text


def test_provider_timeout_is_fallback(settings, payload):
    def handler(request):
        raise httpx.ReadTimeout("simulated timeout", request=request)
    with mocked_client(settings, handler) as client:
        body = client.post("/api/recommend", json=payload).json()
    assert body["mode"] == "fallback"
    assert body["recommendations"]


def test_invalid_json_is_fallback(settings, payload):
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})
    with mocked_client(settings, handler) as client:
        assert client.post("/api/recommend", json=payload).json()["mode"] == "fallback"


def test_reasoning_effort_is_forwarded_only_when_configured(settings, payload):
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(503)
    with mocked_client(settings, handler) as client:
        client.post("/api/recommend", json=payload)
    with mocked_client(replace(settings, llm_reasoning_effort="none"), handler) as client:
        client.post("/api/recommend", json=payload)
    assert "reasoning_effort" not in captured[0]
    assert captured[1]["reasoning_effort"] == "none"


@pytest.mark.parametrize("url", ["https://example.invalid/v1#fragment", "https://example.invalid/v1?key=test", "https://user:password@example.invalid/v1"])
def test_provider_url_cannot_embed_secrets_or_fragments(monkeypatch, url):
    from app.config import Settings
    monkeypatch.setenv("LLM_BASE_URL", url)
    with pytest.raises(ValueError):
        Settings.from_env()
