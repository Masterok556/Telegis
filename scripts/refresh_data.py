"""Refresh Telegis POIs, walking network and official facts in one command.

Each collector publishes its own snapshot atomically and preserves its previous
version on failure. This is not an all-or-nothing transaction across sources.
"""
from pathlib import Path
import subprocess
import sys


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    failed = []
    for script in ('collect_pois.py', 'collect_walk_network.py', 'enrich_pois.py'):
        print('Refreshing: ' + script, flush=True)
        result = subprocess.run([sys.executable, str(root / 'scripts' / script)], cwd=root)
        if result.returncode:
            failed.append(script)
    if failed:
        print('Some sources were not refreshed; their previous snapshots remain: ' + ', '.join(failed))
    else:
        print('All source snapshots refreshed. Verify with python scripts/verify_feature.py')
    raise SystemExit(bool(failed))
