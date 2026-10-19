from dataclasses import replace
from datetime import datetime, timezone
import json

import httpx
from fastapi.testclient import TestClient

from app.generation import Generator
from app.main import create_app
from scripts.collect_pois import publish


def test_text_constraints_are_visible(client, payload):
    body = client.post('/api/recommend', json=payload | {'query': 'Хочу погулять на 20 минут не дальше 500 метров, не музей'}).json()
    context = body['used_context']
    assert context['available_minutes'] == 60
    assert context['effective_minutes'] == 20
    assert context['max_distance_m'] == 500
    assert 'museum' in context['excluded_categories']
    assert all(p['total_minutes_estimate'] <= 20 and p['distance_m'] <= 500 for p in body['recommendations'])


def test_contacts_and_fact_idea_labels_preserved(settings, raw_fixture, payload):
    raw_fixture['elements'][2]['tags'].update({'phone': '+7 000 000 00 00', 'website': 'https://example.invalid/cafe'})
    publish(raw_fixture, settings.data_dir, 'https://example.invalid', 'fixture', datetime.now(timezone.utc).isoformat())
    with TestClient(create_app(settings)) as client:
        body = client.post('/api/recommend', json=payload | {'category': 'cafe', 'query': 'Кофе'}).json()
        place = next(p for p in body['recommendations'] if p['poi_id'] == 'osm_node_3')
        assert place['phone'] == '+7 000 000 00 00'
        assert place['website'] == 'https://example.invalid/cafe'
        assert place['description']
        assert place['fact_source'] == 'OpenStreetMap'
        assert place['activity_source'] == 'suggested_idea'
        quality = client.get('/api/meta').json()['data_quality']
        assert quality['with_contacts'] == 1
        assert quality['confirmed_features']['socket'] == 0


def test_dangerous_website_is_not_exposed(settings, raw_fixture, payload):
    raw_fixture['elements'][2]['tags']['website'] = 'javascript:alert(1)'
    publish(raw_fixture, settings.data_dir, 'https://example.invalid', 'fixture', datetime.now(timezone.utc).isoformat())
    with TestClient(create_app(settings)) as client:
        places = client.post('/api/recommend', json=payload | {'category': 'cafe', 'query': 'Кофе'}).json()['recommendations']
    assert all(p['website'] is None for p in places)


def test_llm_cannot_replace_relevance_order(settings, payload):
    captured = []
    def handler(request):
        context = json.loads(json.loads(request.content)['messages'][1]['content'])
        captured.append(context)
        rows = [{'poi_id': c['poi_id'], 'reason_ids': ['budget'], 'activity_id': next(iter(c['activities']))}
                for c in reversed(context['candidates'])]
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'recommendations': rows})}}]})
    config = replace(settings, llm_api_key='TEST', llm_model='test')
    with TestClient(create_app(config, Generator(config, httpx.MockTransport(handler)))) as client:
        body = client.post('/api/recommend', json=payload | {'query': 'Хочу погулять на 40 минут'}).json()
    assert body['mode'] == 'rag'
    assert captured[0]['intent']['available_minutes'] == 40
    assert [p['poi_id'] for p in body['recommendations']] == [p['poi_id'] for p in captured[0]['candidates']]
    assert len(captured[0]['candidates']) <= 3
