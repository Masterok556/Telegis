"""Probe the actual running HTTP server. --require-rag fails if LLM fell back."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--require-rag", action="store_true")
    parser.add_argument("--category", choices=["walk", "cafe"], default="walk")
    parser.add_argument("--output", type=Path, help="Save a safe report without keys, user text or coordinates")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    def get(path):
        with urllib.request.urlopen(base + path, timeout=25) as response:
            return json.load(response)
    try:
        health, locations = get("/api/health"), get("/api/locations")["locations"]
        location = locations[0]
        payload = {"query": "Хочу кофе" if args.category == "cafe" else "Хочу погулять", "lat": location["lat"], "lon": location["lon"], "available_minutes": 60, "category": args.category}
        request = urllib.request.Request(base + "/api/recommend", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=50) as response:
            body = json.load(response)
        elapsed = round(time.monotonic() - started, 2)
        places = body["recommendations"]
        ok = 1 <= len(places) <= 3 and all(p["total_minutes_estimate"] <= 60 for p in places) and (not args.require_rag or body["mode"] == "rag")
        report = {"checked_at": datetime.now(timezone.utc).isoformat(), "passed": ok,
                  "service": health.get("service"), "poi_count": health["poi_count"], "snapshot_id": health["snapshot_id"],
                  "category": args.category, "mode": body["mode"], "elapsed_seconds": elapsed,
                  "recommendations": [p["name"] for p in places], "message": body["message"]}
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0 if ok else 1
    except (OSError, ValueError, KeyError, IndexError) as exc:
        # No keys or provider body are read by this script.
        print("HTTP-проверка не выполнена: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
