"""Telegis integration checks. Importing this module never starts tests.

python test_suite.py --offline          # isolated app, no paid model calls
python test_suite.py                    # running server on localhost:8000
python test_suite.py --live-llm          # explicitly allow paid model calls

Default server checks do not send successful recommendations to the model.
Run --offline as well to check deterministic recommendation behavior.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import httpx

MEGA = {"lat": 51.0890897, "lon": 71.4073303}


def require(condition: bool, message: str) -> None:
    # Explicit checks continue to work with python -O.
    if not condition:
        raise AssertionError(message)


class Checks:
    def __init__(self, client: Any, positive_recommendations: bool):
        self.client = client
        self.positive_recommendations = positive_recommendations
        self.results: list[dict[str, Any]] = []

    def run(self, name: str, check: Callable[[], None]) -> None:
        try:
            check()
            result = {"test": name, "pass": True}
        except Exception as exc:
            # Never print response bodies, credentials or rejected user input.
            detail = str(exc) if isinstance(exc, AssertionError) else type(exc).__name__
            result = {"test": name, "pass": False, "details": detail}
        self.results.append(result)
        print(f"{'PASS' if result['pass'] else 'FAIL'} {name}"
              + (f": {result['details']}" if "details" in result else ""))

    def request(self, method: str, path: str, body: dict | None = None,
                status: int = 200) -> tuple[httpx.Response, dict]:
        response = self.client.request(method, path, **({"json": body} if body is not None else {}))
        require(response.status_code == status,
                f"Expected HTTP {status}, received {response.status_code}")
        require(response.headers.get("cache-control") == "no-store", "Missing API no-store")
        require(response.headers.get("x-content-type-options") == "nosniff", "Missing nosniff")
        require(response.headers.get("referrer-policy") == "no-referrer", "Missing no-referrer")
        data = response.json()
        require(isinstance(data, dict), "Expected a JSON object")
        return response, data

    def health(self) -> None:
        _, body = self.request("GET", "/api/health")
        require(body.get("status") == "ok", "Dataset is not ready")
        require(body.get("service") == "Telegis", "Incorrect service name")
        require(body.get("poi_count", 0) > 0 and bool(body.get("snapshot_id")), "Missing dataset identity")

    def metadata(self) -> None:
        _, body = self.request("GET", "/api/meta")
        require(body.get("service") == "Telegis", "Incorrect service name")
        require(body.get("poi_count", 0) > 0, "No POIs")
        require(bool(body.get("license") and body.get("collected_at") and body.get("privacy")),
                "Missing attribution, collection date or privacy disclosure")
        require(body.get("walking_network", {}).get("available") is True, "Walking graph unavailable")
        require(body.get("data_quality", {}).get("attributed_fact_count", 0) > 0, "No attributed facts")

    def locations(self) -> None:
        _, body = self.request("GET", "/api/locations")
        rows = body.get("locations", [])
        require(bool(rows), "No starting locations")
        require(any("mega" in item.get("name", "").lower() for item in rows), "Mega anchor missing")
        for item in rows:
            require(bool(item.get("id") and item.get("name")), "Location identity missing")
            require(50 < item["lat"] < 52 and 70 < item["lon"] < 73, "Invalid Astana coordinate")

    def pois(self) -> None:
        _, body = self.request("GET", "/api/pois")
        _, meta = self.request("GET", "/api/meta")
        rows = body.get("pois", [])
        require(len(rows) == meta["poi_count"], "POI catalog count differs from manifest")
        require(len({item["poi_id"] for item in rows}) == len(rows), "Duplicate POI IDs")
        for item in rows:
            require(50 < item["lat"] < 52 and 70 < item["lon"] < 73, "Invalid Astana coordinate")
            self.source(item)

    @staticmethod
    def source(item: dict) -> None:
        require(item.get("source_url", "").startswith("https://www.openstreetmap.org/"),
                "POI has no canonical OSM source")
        require(bool(item.get("collected_at")), "POI collection timestamp missing")

    def invalid(self, endpoint: str, payload: dict) -> None:
        _, body = self.request("POST", endpoint, payload, 422)
        require(isinstance(body.get("detail"), list), "Validation errors missing")
        require(all("input" not in error and "ctx" not in error for error in body["detail"]),
                "Validation response exposes rejected input")

    def no_recommendations(self, query: str, **changes: Any) -> None:
        payload = {**MEGA, "query": query, "category": "cafe", "available_minutes": 90, **changes}
        _, body = self.request("POST", "/api/recommend", payload)
        require(body.get("recommendations") == [], "Unsupported constraint silently ignored")
        require(bool(body.get("message")), "Empty result needs an explanation")
        require(body.get("mode") == "fallback", "No-match should not claim model generation")

    def recommendation(self, category: str) -> None:
        payload = {**MEGA, "query": "Хочу погулять" if category == "walk" else "Хочу кофе",
                   "category": category, "available_minutes": 90}
        _, body = self.request("POST", "/api/recommend", payload)
        rows = body.get("recommendations", [])
        require(1 <= len(rows) <= 3, "Expected 1-3 grounded recommendations")
        require(body.get("mode") in {"rag", "fallback"}, "Unknown generation mode")
        _, catalog = self.request("GET", "/api/pois")
        ids = {item["poi_id"] for item in catalog["pois"]}
        for item in rows:
            require(item["poi_id"] in ids, "Recommendation is outside the dataset")
            if category == "cafe":
                require(item["category"] == "cafe", "Cafe filter ignored")
            require(bool(item.get("why") and item.get("activity")), "Missing explanation or activity")
            require(item["total_minutes_estimate"] <= body["used_context"]["effective_minutes"],
                    "Recommendation exceeds the time budget")
            require(item["total_minutes_estimate"] == 2 * item["walk_minutes_estimate"] + item["visit_minutes_estimate"],
                    "Recommendation return time is not included")
            require(item["time_margin_minutes"] == body["used_context"]["effective_minutes"] - item["total_minutes_estimate"],
                    "Incorrect remaining time")
            require(item["activity_source"] == "suggested_idea", "Activity is mislabeled as fact")
            require(item["travel_basis"] == "osm_walking_graph", "Expected graph-based time")
            require(bool(item["warnings"]), "Missing uncertainty warnings")
            self.source(item)

    def itinerary(self, minutes: int, ready: bool = True, **changes: Any) -> dict:
        payload = {**MEGA, "query": "Хочу погулять", "available_minutes": minutes,
                   "include_coffee": True, **changes}
        _, body = self.request("POST", "/api/itinerary", payload)
        require(body.get("mode") == "local_graph", "Itinerary is not locally calculated")
        if not ready:
            require(body.get("status") == "no_match", "Expected an honest refusal")
            require(body.get("stops") == [] and body.get("legs") == [] and body.get("route_coordinates") == [],
                    "Rejected itinerary still exposes a route")
            require(bool(body.get("message")), "Rejection has no explanation")
            return body
        require(body.get("status") == "ready", "Expected a feasible itinerary")
        stops, legs = body["stops"], body["legs"]
        require(2 <= len(stops) <= 3 and len(legs) == len(stops) + 1, "Missing stops or return leg")
        require(len({stop["poi_id"] for stop in stops}) == len(stops), "Duplicate route stops")
        budget = body["used_context"]["effective_minutes"]
        require(body["total_minutes_estimate"] <= budget <= minutes, "Route exceeds effective budget")
        require(body["total_minutes_estimate"] == body["walking_minutes_estimate"]
                + body["visit_minutes_estimate"] + body["reserve_minutes"], "Incorrect time accounting")
        require(body["reserve_minutes"] >= 5, "No time reserve")
        require(body["remaining_minutes"] == budget - body["total_minutes_estimate"], "Incorrect free time")
        require(sum(leg["walk_minutes_estimate"] for leg in legs) == body["walking_minutes_estimate"],
                "Leg times do not sum to total")
        require(sum(stop["visit_minutes_estimate"] for stop in stops) == body["visit_minutes_estimate"],
                "Visit times do not sum to total")
        require(body["used_context"]["return_to_start"] is True, "Return to start missing")
        require(body["network_snapshot_id"] and body["network_collected_at"], "Graph provenance missing")
        coords = body["route_coordinates"]
        start = [payload["lon"], payload["lat"]]
        require(coords[0] == start and coords[-1] == start, "Polyline does not return to start")
        require(all(70 < point[0] < 73 and 50 < point[1] < 52 for point in coords),
                "Coordinates must use longitude, latitude")
        for index, leg in enumerate(legs):
            require(leg["route_kind"] == "osm_walking_graph_with_approximate_connectors",
                    "Route method is mislabeled")
            require(len(leg["coordinates"]) >= 2, "Missing route geometry")
            require(leg["distance_m"] >= 0 and leg["connector_m"] >= 0, "Invalid distances")
            if index:
                require(legs[index - 1]["coordinates"][-1] == leg["coordinates"][0], "Polyline has a gap")
        for stop in stops:
            require(stop["departure_minutes_estimate"] - stop["arrival_minutes_estimate"]
                    == stop["visit_minutes_estimate"], "Incorrect stop timing")
            require(bool(stop["why"] and stop["activity"] and stop["warnings"]), "Incomplete stop explanation")
            self.source(stop)
        return body

    def minimum_budget(self) -> None:
        body = self.itinerary(60, ready=False)
        minimum = body.get("suggested_minimum_minutes")
        require(isinstance(minimum, int) and 60 < minimum <= 180, "Missing feasible budget suggestion")
        self.itinerary(minimum)

    def protected_files(self) -> None:
        for path in ("/.env", "/.git/config", "/static/.env", "/app/config.py", "/data/current.json"):
            response = self.client.get(path)
            require(response.status_code in {403, 404}, f"Private path was served: {path}")

    def poi_details(self) -> None:
        _, catalog = self.request("GET", "/api/pois")
        item = next(p for p in catalog["pois"] if p.get("recommendable", True))
        _, info = self.request("POST", "/api/poi_ai_info", {"poi_id": item["poi_id"]})
        require(info.get("mode") == "sourced" and info.get("activity_source") == "suggested_idea",
                "Details are not labeled as sourced facts and a suggested activity")
        require(bool(info.get("summary") and info.get("tip")), "Missing summary or activity")
        require(info.get("source_url") == item["source_url"], "POI details source mismatch")
        self.request("POST", "/api/poi_ai_info", {"poi_id": "osm_node_999999999999999"}, 404)

    def execute(self) -> list[dict[str, Any]]:
        self.run("Health and dataset identity", self.health)
        self.run("Sources, graph and privacy metadata", self.metadata)
        self.run("Starting locations", self.locations)
        self.run("Catalog matches manifest", self.pois)
        self.run("Sourced POI details and unknown ID", self.poi_details)
        self.run("Private files cannot be downloaded", self.protected_files)
        rec = {**MEGA, "query": "Хочу кофе", "category": "cafe", "available_minutes": 90}
        route = {**MEGA, "query": "Хочу погулять", "include_coffee": True, "available_minutes": 120}
        cases = [
            ("Recommend rejects route-only field", "/api/recommend", {**rec, "include_coffee": True}),
            ("Itinerary rejects recommendation-only field", "/api/itinerary", {**route, "category": "walk"}),
            ("Empty query rejected", "/api/recommend", {**rec, "query": ""}),
            ("Invalid coordinate rejected privately", "/api/recommend", {**rec, "lat": 91.123456789}),
            ("Boolean time rejected", "/api/recommend", {**rec, "available_minutes": True}),
            ("Missing itinerary start rejected", "/api/itinerary", {"available_minutes": 120}),
            ("Non-boolean coffee rejected", "/api/itinerary", {**route, "include_coffee": "false"}),
        ]
        for name, endpoint, payload in cases:
            self.run(name, lambda e=endpoint, p=payload: self.invalid(e, p))
        self.run("Unverified sockets are not invented", lambda: self.no_recommendations("Кофе с розеткой"))
        self.run("Opening-now condition is not invented", lambda: self.no_recommendations("Кофе открыто сейчас"))
        self.run("Outside coverage returns explanation", lambda: self.no_recommendations("Хочу кофе", lat=43.238, lon=76.945))
        self.run("120-minute route, graph and return", lambda: self.itinerary(120))
        self.run("90-minute route stays within budget", lambda: self.itinerary(90))
        self.run("Short route refuses and suggests feasible time", self.minimum_budget)
        self.run("Contradictory coffee setting refuses", lambda: self.itinerary(120, ready=False, query="Хочу погулять без кофе"))
        self.run("Accessibility is not invented", lambda: self.itinerary(120, ready=False, query="Маршрут для инвалидной коляски"))
        self.run("Text time limit is respected", lambda: self.itinerary(120, ready=False, query="Прогулка на 20 минут"))
        if self.positive_recommendations:
            self.run("Grounded walking recommendations", lambda: self.recommendation("walk"))
            self.run("Grounded coffee recommendations", lambda: self.recommendation("cafe"))
        else:
            print("SKIP positive recommendations: use --offline (free) or --live-llm (provider fees may apply)")
        return self.results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Running Telegis server")
    parser.add_argument("--offline", action="store_true", help="Test local app with model disabled and no network")
    parser.add_argument("--live-llm", action="store_true", help="Allow successful recommendation requests to the configured model")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds")
    parser.add_argument("--output", type=Path, help="Optional JSON report path (no file written by default)")
    args = parser.parse_args(argv)
    parsed = urlsplit(args.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        parser.error("--base-url must be an HTTP(S) server URL without credentials")
    if not 0 < args.timeout <= 120:
        parser.error("--timeout must be greater than 0 and at most 120")
    if args.offline and args.live_llm:
        parser.error("--offline and --live-llm are mutually exclusive")
    if args.offline:
        from fastapi.testclient import TestClient
        from app.config import Settings
        from app.main import create_app
        context = TestClient(create_app(Settings(llm_api_key="", llm_model="")))
    else:
        context = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=args.timeout,
                               follow_redirects=False, trust_env=False)
    print(f"Telegis integration checks ({'offline app, model disabled' if args.offline else 'running server'})")
    with context as client:
        results = Checks(client, args.offline or args.live_llm).execute()
    passed = sum(item["pass"] for item in results)
    report = {"mode": "offline" if args.offline else "server", "live_llm_allowed": args.live_llm,
              "passed": passed, "total": len(results), "results": results}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
