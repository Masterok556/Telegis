"""Audit v1.2 on shipped real snapshots, without paid API calls or user locations."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.config import Settings
from app.data_store import DataStore
from app.facts import excluded_from_routes, facts_for
from app.main import create_app


def main():
    ds = DataStore(ROOT / 'data').get()
    docs = ROOT / 'docs'
    checks = []
    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
    settings = Settings(llm_api_key='', llm_model='')
    with TestClient(create_app(settings)) as client:
        meta = client.get('/api/meta').json()
        first = ds.locations[0]
        base = {'lat': first.lat, 'lon': first.lon, 'query': 'Хочу погулять', 'include_coffee': True}
        started = time.monotonic()
        ready = client.post('/api/itinerary', json=base | {'available_minutes': 120}).json()
        elapsed = round(time.monotonic() - started, 3)
        tight = client.post('/api/itinerary', json=base | {'available_minutes': 60}).json()
        check('Real 3-stop route at 120 minutes', ready['status'] == 'ready' and len(ready['stops']) == 3)
        check('All legs include return to start', len(ready['legs']) == len(ready['stops']) + 1 and ready['legs'][-1]['to_id'] == 'start')
        check('Complete time accounting', ready['total_minutes_estimate'] == ready['walking_minutes_estimate'] + ready['visit_minutes_estimate'] + ready['reserve_minutes'] <= 120)
        check('Reserve at least 10 percent', ready['reserve_minutes'] >= 12)
        check('Strict 60-minute refusal with actionable budget', tight['status'] == 'no_match' and 60 < (tight['suggested_minimum_minutes'] or 0) <= 180)
        if tight['suggested_minimum_minutes']:
            retry = client.post('/api/itinerary', json=base | {'available_minutes': tight['suggested_minimum_minutes']}).json()
            check('Suggested budget actually works', retry['status'] == 'ready')
        known = {p.poi_id for p in ds.pois}
        check('Every stop is a real stored POI', all(p['poi_id'] in known for p in ready['stops']))
        check('No held construction project in route', all(not excluded_from_routes(p) for p in ds.pois if p.poi_id in {s['poi_id'] for s in ready['stops']}))
        japanese = next(p for p in ds.pois if p.name == 'Японский сад')
        recommendation = client.post('/api/recommend', json={'lat': first.lat, 'lon': first.lon,
            'available_minutes': 120, 'category': 'walk', 'query': 'Хочу японский сад с камнями'}).json()
        jp = next((p for p in recommendation['recommendations'] if p['poi_id'] == japanese.poi_id), None)
        check('Specific sourced explanation for Japanese garden', jp and 'камн' in jp['why'] and any(e['kind'] == 'official' for e in jp['evidence']))
        check('Graph-based time on ordinary recommendation', jp and jp['travel_basis'] == 'osm_walking_graph' and jp['route_distance_m'] > jp['distance_m'])
        check('Historical source warning preserved', jp and any('2019' in w for w in jp['warnings']))
        check('Unknown sockets not invented', client.post('/api/recommend', json={'lat': first.lat,'lon': first.lon,'available_minutes':120,'category':'cafe','query':'Кафе с розеткой'}).json()['recommendations'] == [])
        report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'passed': all(c['passed'] for c in checks),
                  'checks': checks, 'data_quality': meta['data_quality'], 'walking_network': meta['walking_network'],
                  'itinerary_elapsed_seconds': elapsed, 'paid_llm_calls': 0}
        files = {'feature-verification.json': report, 'itinerary-example.json': ready,
                 'itinerary-too-short.json': tight, 'enriched-recommendation-example.json': recommendation}
        for name, value in files.items():
            (docs / name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in checks:
        print(('PASS ' if row['passed'] else 'FAIL ') + row['name'])
    print('itinerary_elapsed_seconds:', elapsed)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
