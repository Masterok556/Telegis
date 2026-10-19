"""Probe the actual running HTTP server. --require-rag fails if LLM fell back."""
import argparse
import json
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--require-rag", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    def get(path):
        with urllib.request.urlopen(base + path, timeout=25) as response:
            return json.load(response)
    try:
        health, locations = get("/api/health"), get("/api/locations")["locations"]
        location = locations[0]
        payload = {"query": "Хочу погулять", "lat": location["lat"], "lon": location["lon"], "available_minutes": 60, "category": "walk"}
        request = urllib.request.Request(base + "/api/recommend", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=50) as response:
            body = json.load(response)
        ok = bool(body["recommendations"]) and (not args.require_rag or body["mode"] == "rag")
        print(json.dumps({"passed": ok, "poi_count": health["poi_count"], "mode": body["mode"],
                          "recommendations": [p["name"] for p in body["recommendations"]], "message": body["message"]}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    except (OSError, ValueError, KeyError, IndexError) as exc:
        # No keys or provider body are read by this script.
        print("HTTP-проверка не выполнена: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
