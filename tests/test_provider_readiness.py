from dataclasses import replace
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.generation import Generator
from app.main import create_app


@pytest.mark.parametrize('host,parameter', [('https://openrouter.ai/api/v1', 'max_tokens'),
                                          ('https://api.openai.com/v1', 'max_completion_tokens')])
def test_provider_output_is_bounded(settings, payload, host, parameter):
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(402, text='private provider details')
    config = replace(settings, llm_base_url=host, llm_api_key='TEST', llm_model='test', llm_max_tokens=1200)
    with TestClient(create_app(config, Generator(config, httpx.MockTransport(handler)))) as client:
        response = client.post('/api/recommend', json=payload)
        assert response.json()['mode'] == 'fallback'
        assert client.get('/api/health').json()['llm_last_status'] == 'credits'
    assert captured[0][parameter] == 1200
    assert 'private provider details' not in response.text


@pytest.mark.parametrize('status,expected', [(401, 'authentication'), (402, 'credits'), (404, 'model_unavailable'),
                                          (429, 'rate_limit'), (503, 'provider_error')])
def test_safe_operational_diagnostics(settings, payload, status, expected):
    config = replace(settings, llm_api_key='TEST-SECRET', llm_model='test')
    transport = httpx.MockTransport(lambda request: httpx.Response(status, text='private upstream text TEST-SECRET'))
    with TestClient(create_app(config, Generator(config, transport))) as client:
        assert client.get('/api/health').json()['llm_last_status'] == 'not_checked'
        response = client.post('/api/recommend', json=payload)
        assert response.status_code == 200
        assert response.json()['recommendations']
        health = client.get('/api/health')
        assert health.json()['llm_last_status'] == expected
        assert health.json()['service'] == 'Telegis'
        assert 'TEST-SECRET' not in response.text + health.text
        assert 'private upstream text' not in response.text + health.text


@pytest.mark.parametrize('limit', ['0', '-1', '500000', 'nan'])
def test_invalid_token_budget_rejected(monkeypatch, limit):
    monkeypatch.setenv('LLM_MAX_TOKENS', limit)
    with pytest.raises(ValueError):
        Settings.from_env()
