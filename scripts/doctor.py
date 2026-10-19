"""Telegis readiness check. Offline by default; --live makes one provider request."""
import argparse
import asyncio
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.data_store import DataStore, DatasetUnavailable
from app.generation import Generator
from app.models import RecommendRequest
from app.retrieval import retrieve


async def check(live):
    try:
        settings = Settings.from_env()
        dataset = DataStore(settings.data_dir).get()
    except (ValueError, OSError, DatasetUnavailable):
        return {'passed': False, 'message': 'Invalid configuration or dataset. Check .env and data/current.json; no secrets are printed.'}
    result = {'service': 'Telegis', 'passed': True, 'poi_count': len(dataset.pois),
              'categories': dict(Counter(p.category for p in dataset.pois)),
              'snapshot_id': dataset.manifest['snapshot_id'], 'llm_configured': settings.llm_configured,
              'provider_checked': False, 'frontend_present': (settings.static_dir / 'index.html').is_file()}
    if not live:
        result['next_step'] = 'Use --live to verify the model; configuration alone does not prove RAG works.'
        return result
    location = dataset.locations[0]
    request = RecommendRequest(query='Хочу погулять', lat=location.lat, lon=location.lon,
                               category='walk', available_minutes=60)
    found = retrieve(request, dataset)
    if not found.candidates:
        return result | {'passed': False, 'message': 'No candidates for the built-in demo scenario.'}
    generator = Generator(settings)
    response = await generator.generate(request, found.candidates, found.required_features)
    return result | {'passed': response.mode == 'rag', 'provider_checked': settings.llm_configured,
                     'mode': response.mode, 'llm_status': generator.last_status, 'message': response.message}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='One request billed by your provider')
    args = parser.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    report = asyncio.run(check(args.live))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
