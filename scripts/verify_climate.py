"""Reproducible API checks: synthetic weather, real shipped POIs and OSM paths.

Run: python -m scripts.verify_climate
No external HTTP, API key, .env load, device location or paid model is used.
Weather fixtures here are test inputs, never evidence of actual Astana weather.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from math import ceil
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

import httpx
from fastapi.testclient import TestClient

from app.climate import indoor_evidence
from app.config import Settings
from app.data_store import DataStore
from app.facts import excluded_from_routes
with patch.object(Settings, "from_env", return_value=Settings(llm_api_key="", llm_model="")):
    # app.main exports a default app at import time; isolate that initialization too.
    from app.main import create_app
from app.weather import (
    WeatherCurrent, WeatherService, WeatherSnapshot, climate_policy, demo_snapshot,
    unknown_policy,
)
from app.walking import WalkingNetwork


FIXTURE_TIME = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)


def fixture(status="live", apparent=10) -> WeatherSnapshot:
    """Synthetic status/time/values for deterministic integration assertions."""
    if status == "demo":
        return demo_snapshot()
    current = WeatherCurrent(
        temperature_c=apparent, apparent_temperature_c=apparent,
        wind_m_s=2, gust_m_s=3, precipitation_mm=0,
        precipitation_interval_seconds=900, weather_code=2, is_day=True,
    )
    age = 7200 if status == "stale" else 0
    available = status != "unavailable"
    return WeatherSnapshot(
        status=status, source="Synthetic integration test fixture", source_url=None,
        valid_at=FIXTURE_TIME - timedelta(seconds=age) if available else None,
        fetched_at=FIXTURE_TIME - timedelta(seconds=age) if available else None,
        age_seconds=age if available else None, current=current if available else None,
        policy=climate_policy(current) if status == "live" else unknown_policy("test_fixture"),
        warnings=["Synthetic weather test input; not actual weather."],
        attribution="Synthetic weather test fixture; no Open-Meteo request.",
    )


class FixtureWeatherService(WeatherService):
    def __init__(self, value: WeatherSnapshot):
        super().__init__(enabled=False)
        self.value = value
        self.calls: list[bool] = []

    async def get(self, demo=False) -> WeatherSnapshot:
        self.calls.append(demo)
        return demo_snapshot() if demo else self.value.model_copy(deep=True)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def api_json(client, path, payload=None):
    response = client.get(path) if payload is None else client.post(path, json=payload)
    require(response.status_code == 200, f"{path}: HTTP {response.status_code}")
    require(response.headers.get("Cache-Control") == "no-store", f"{path}: missing privacy header")
    return response.json()


def ids(body, key="recommendations"):
    return [row["poi_id"] for row in body[key]]


def verify() -> dict:
    dataset = DataStore(ROOT / "data").get()
    network = WalkingNetwork.load(ROOT / "data" / "walking")
    coverage = dataset.manifest["coverage"]
    start = (coverage["lat"], coverage["lon"])  # Public collection center, not user GPS.
    origin = {"lat": start[0], "lon": start[1]}
    walk = origin | {"query": "Прогулка", "category": "walk", "available_minutes": 120}
    coffee = walk | {"query": "Кофе", "category": "cafe"}
    loop = origin | {"query": "Прогулка и кофе", "include_coffee": True, "available_minutes": 120}
    indoor = {p.poi_id: p for p in dataset.pois if p.category == "cafe" and indoor_evidence(p)}
    require(len(indoor) == 3, "Expected three source-verified indoor cafés in this shipped snapshot")
    target = next(iter(sorted(indoor)))
    indoor_origin = {"lat": indoor[target].lat, "lon": indoor[target].lon}
    route = origin | {"poi_id": target}
    disconnected = next((p for p in dataset.pois if not excluded_from_routes(p)
                         and network.route(start, (p.lat, p.lon)) is None), None)
    require(disconnected is not None, "Expected a real POI without a graph path for the refusal test")
    settings = Settings(llm_api_key="", llm_model="", walking_dir=ROOT / "data" / "walking")
    checks = []

    def client_for(value):
        weather = FixtureWeatherService(value)
        return TestClient(create_app(settings, weather_service=weather)), weather

    def case(name, run):
        try:
            details = run()
            checks.append({"name": name, "passed": True, "syntheticWeatherTest": True, "details": details})
        except Exception as exc:
            checks.append({"name": name, "passed": False, "syntheticWeatherTest": True,
                           "error": f"{type(exc).__name__}: {str(exc)[:300]}"})

    def disabled():
        client, weather = client_for(fixture(apparent=-15))
        with client:
            result = api_json(client, "/api/recommend", coffee)
        require(result["recommendations"], "Ordinary coffee search unexpectedly empty")
        require(not weather.calls, "Disabled climate mode contacted weather")
        require(result["used_context"]["climate"]["policy"] == "off", "Disabled policy differs")
        return {"weather_calls": 0, "poi_ids": ids(result)}

    def normal():
        client, _ = client_for(fixture())
        with client:
            off = api_json(client, "/api/recommend", walk)
            on = api_json(client, "/api/recommend", walk | {"climate_shield": True})
        require(ids(off) == ids(on) and ids(on), "Normal weather changed candidate ordering")
        require([r["total_minutes_estimate"] for r in off["recommendations"]]
                == [r["total_minutes_estimate"] for r in on["recommendations"]], "Normal weather changed time")
        climate = on["used_context"]["climate"]
        require(climate["applied"] and climate["policy"] == "normal", "Normal adaptation not explicit")
        return {"same_poi_ids": ids(on), "policy": climate["policy"]}

    def indoor_cafes():
        client, _ = client_for(fixture(apparent=-15))
        with client:
            result = api_json(client, "/api/recommend", coffee | indoor_origin | {"climate_shield": True})
        require(set(ids(result)) == set(indoor), "Cold-weather results differ from the three proven indoor cafés")
        require(result["used_context"]["climate"]["policy"] == "indoor_only", "Missing indoor-only policy")
        for row in result["recommendations"]:
            expected = indoor[row["poi_id"]]
            require(row["climate_shielded"] and row["indoor_evidence"], "Missing indoor evidence")
            require(all(e["source_url"] == expected.source_url for e in row["indoor_evidence"]), "Evidence source changed")
            require(any("Переходы до них остаются уличными" in w for w in row["warnings"]), "Outdoor travel caveat missing")
        return {"public_start_poi_id": target, "poi_ids": ids(result),
                "evidence": [{"poi_id": p.poi_id, "source_url": p.source_url,
                              "indoor_tags": {k: v for k, v in p.tags.items() if k in {"indoor", "indoor_seating"}}}
                             for p in indoor.values()]}

    def indoor_cafes_outside_radius():
        client, _ = client_for(fixture(apparent=-15))
        with client:
            result = api_json(client, "/api/recommend", coffee | {"climate_shield": True})
        require(result["recommendations"] == [], "Climate silently widened the EXPO search radius")
        require(result["used_context"]["max_distance_m"] == 2500, "Default radius changed")
        require(result["used_context"]["climate"]["policy"] == "indoor_only", "Indoor constraint missing")
        return {"public_start": "dataset_coverage_center", "search_radius_m": 2500,
                "recommendation_count": 0,
                "reason": "The three source-verified indoor cafés are outside the EXPO-center search radius."}

    def indoor_walk_refused():
        client, _ = client_for(fixture(apparent=-15))
        with client:
            recommendation = api_json(client, "/api/recommend", walk | {"climate_shield": True})
            itinerary = api_json(client, "/api/itinerary", loop | {"climate_shield": True})
        require(not recommendation["recommendations"], "Outdoor walking recommendation leaked into cold mode")
        require(itinerary["status"] == "no_match" and not itinerary["stops"]
                and not itinerary["route_coordinates"], "Cold route added unsupported outdoor stops")
        return {"recommendation_count": 0, "itinerary_status": "no_match"}

    def paused(status, apparent):
        client, _ = client_for(fixture(status, apparent))
        with client:
            rec = api_json(client, "/api/recommend", coffee | {"climate_shield": True})
            itin = api_json(client, "/api/itinerary", loop | {"climate_shield": True})
            point = api_json(client, "/api/route", route | {"climate_shield": True})
        require(not rec["recommendations"] and not itin["stops"] and not point["coordinates"], "Paused climate produced a result")
        require(itin["status"] == point["status"] == "no_match", "Paused route did not refuse")
        for body in (rec, itin, point):
            require(body["used_context"]["climate"]["policy"] == "paused", "Paused policy missing")
            require(body["used_context"]["climate"]["weather"]["status"] == status, "Weather status rewritten")
        return {"weather_fixture_status": status, "apparent_temperature_c": apparent,
                "endpoints_refused": ["/api/recommend", "/api/itinerary", "/api/route"]}

    def demo_isolation():
        client, weather = client_for(fixture())
        with client:
            sample = api_json(client, "/api/weather?demo=true")
            real = api_json(client, "/api/recommend", coffee | {"climate_shield": True})
        require(sample["status"] == "demo" and sample["source"] == "Telegis demo", "Demo not labeled")
        require(sample["valid_at"] is None and sample["fetched_at"] is None, "Demo claimed observation time")
        require(real["used_context"]["climate"]["policy"] == "normal", "Demo contaminated subsequent decision")
        require(real["used_context"]["climate"]["weather"]["source"] == "Synthetic integration test fixture", "Default fixture replaced")
        require(weather.calls == [True, False], "Recommendation incorrectly requested demo")
        return {"demo_status": sample["status"], "following_policy": "normal", "weather_demo_arguments": weather.calls}

    def check_loop(result):
        require(result["status"] == "ready", "No connected loop in the saved graph")
        require(len(result["stops"]) >= 2 and len(set(ids(result, "stops"))) == len(result["stops"]), "Stops duplicate or missing")
        require(result["route_coordinates"][0] == result["route_coordinates"][-1], "Loop not closed")
        require(result["legs"][-1]["to_id"] == "start", "Return leg missing")
        total = sum(leg["walk_minutes_estimate"] for leg in result["legs"])
        total += sum(stop["visit_minutes_estimate"] for stop in result["stops"]) + result["reserve_minutes"]
        require(result["total_minutes_estimate"] == total <= 120, "Budget arithmetic invalid")
        require(result["reserve_minutes"] >= 12, "Reserve is less than 10 percent")
        by_id = {p.poi_id: (p.lat, p.lon) for p in dataset.pois} | {"start": start}
        for leg in result["legs"]:
            expected = network.route(by_id[leg["from_id"]], by_id[leg["to_id"]])
            require(expected is not None and leg["coordinates"] == expected.coordinates, "Leg geometry is not the saved graph path")
            require(leg["distance_m"] == expected.distance_m, "Leg distance changed")

    def loop_accounting():
        client, _ = client_for(fixture())
        with client:
            off = api_json(client, "/api/itinerary", loop)
            on = api_json(client, "/api/itinerary", loop | {"climate_shield": True})
        check_loop(off)
        check_loop(on)
        require(ids(off, "stops") == ids(on, "stops"), "Normal weather changed loop stops")
        require(off["route_coordinates"] == on["route_coordinates"], "Normal weather changed loop geometry")
        return {"poi_ids": ids(on, "stops"), "legs": len(on["legs"]),
                "total_minutes": on["total_minutes_estimate"], "reserve_minutes": on["reserve_minutes"],
                "coordinates_checked_against_saved_graph": True}

    def connected_point(cold=False):
        client, weather = client_for(fixture(apparent=-15 if cold else 10))
        with client:
            result = api_json(client, "/api/route", route | {"climate_shield": cold})
        p = indoor[target]
        expected = network.route(start, (p.lat, p.lon))
        require(result["status"] == "ready" and expected, "Known connected café has no route")
        require(result["coordinates"] == expected.coordinates and len(result["coordinates"]) > 2, "Point route is not graph geometry")
        require(result["distance_m"] == expected.distance_m, "Point distance differs from graph")
        require(result["walk_minutes_estimate"] == max(1, ceil(expected.distance_m / 70)), "Point timing invalid")
        require(result["used_context"]["return_to_start"] is False, "Point route falsely includes return")
        require(any("одну сторону" in text for text in result["warnings"]), "One-way caveat missing")
        if cold:
            require(result["used_context"]["climate"]["policy"] == "indoor_only", "Cold point route not filtered")
        else:
            require(not weather.calls, "Unrequested climate fetched weather")
        return {"poi_id": target, "distance_m": result["distance_m"],
                "walk_minutes": result["walk_minutes_estimate"], "geometry_vertices": len(result["coordinates"]),
                "one_way": True, "cold_fixture": cold}

    def disconnected_point():
        client, _ = client_for(fixture())
        with client:
            result = api_json(client, "/api/route", origin | {"poi_id": disconnected.poi_id})
        require(result["status"] == "no_match" and not result["coordinates"], "A nonexistent graph route was drawn")
        require(result["distance_m"] == 0 and result["walk_minutes_estimate"] == 0, "Missing route has invented distance/time")
        return {"poi_id": disconnected.poi_id, "source_url": disconnected.source_url,
                "status": "no_match", "geometry_vertices": 0}

    def localized(locale):
        client, _ = client_for(fixture())
        with client:
            rec = api_json(client, "/api/recommend", coffee | {"locale": locale, "climate_shield": True})
            itin = api_json(client, "/api/itinerary", loop | {"locale": locale})
            point = api_json(client, "/api/route", route | {"locale": locale})
            info = api_json(client, "/api/poi_ai_info", {"poi_id": target, "locale": locale})
            weather = api_json(client, "/api/weather?locale=" + locale)
            meta = api_json(client, "/api/meta?locale=" + locale)
            catalog = api_json(client, "/api/pois?locale=" + locale)
        require(rec["recommendations"] and point["status"] == "ready", "Localized endpoint changed availability")
        check_loop(itin)
        require(len(catalog["pois"]) == len(dataset.pois), "Localization changed dataset size")
        known = {p.poi_id: p for p in dataset.pois}
        for row in catalog["pois"]:
            p = known[row["poi_id"]]
            require(row["name"] == p.name and row["source_url"] == p.source_url and row["tags"] == p.tags
                    and row["opening_hours"] == p.opening_hours, "Localization changed raw source identity")
        require(rec["used_context"]["locale"] == locale and point["used_context"]["locale"] == locale, "Locale lost")
        for body in (rec, itin, point, info, weather, meta):
            text = json.dumps(body, ensure_ascii=False)
            require("[Original source text]" not in text and "[Дереккөз мәтіні: түпнұсқа]" not in text,
                    "Current API text fell back to untranslated source prose")
        expected = {"ru": "Модель не подключена.", "en": "The language model is not connected.",
                    "kz": "Тілдік модель қосылмаған."}[locale]
        require(rec["message"].startswith(expected), "Main API message is in the wrong language")
        return {"locale": locale, "endpoints_checked": 7, "catalog_count": len(catalog["pois"]),
                "source_identities_preserved": True, "mini_route_status": itin["status"]}

    network_attempts = []
    def forbid_sync(*_args, **_kwargs):
        network_attempts.append("sync")
        raise AssertionError("External HTTP is prohibited in this verification")
    async def forbid_async(*_args, **_kwargs):
        network_attempts.append("async")
        raise AssertionError("External HTTP is prohibited in this verification")

    with patch.object(httpx.HTTPTransport, "handle_request", forbid_sync), \
            patch.object(httpx.AsyncHTTPTransport, "handle_async_request", forbid_async):
        case("Climate off makes no weather request", disabled)
        case("Normal weather preserves recommendations and times", normal)
        case("Cold weather returns exactly three sourced indoor cafés", indoor_cafes)
        case("Cold weather does not silently widen EXPO search radius", indoor_cafes_outside_radius)
        case("Cold weather refuses unsupported outdoor stops and loops", indoor_walk_refused)
        for name, status, temperature in [("Stale weather", "stale", -15), ("Unavailable weather", "unavailable", 10),
                                           ("Severe cold", "live", -25), ("Injected demo weather", "demo", -18)]:
            case(name + " pauses all climate-enabled endpoints", lambda s=status, t=temperature: paused(s, t))
        case("Explicit demo is labeled and isolated", demo_isolation)
        case("Real graph loop preserves return, reserve and budget", loop_accounting)
        case("Single destination follows the real graph and is one-way", connected_point)
        case("Cold single-destination route accepts sourced indoor café", lambda: connected_point(True))
        case("Missing real graph connection yields no invented geometry", disconnected_point)
        for locale in ("ru", "kz", "en"):
            case("API localization preserves facts: " + locale, lambda lang=locale: localized(lang))

    return {
        "schema_version": 1, "checked_at": datetime.now(timezone.utc).isoformat(),
        "syntheticWeatherTest": True,
        "weather_test_notice": "All weather states and values are synthetic integration test inputs, not actual Astana weather.",
        "real_dataset_snapshot": dataset.manifest["snapshot_id"], "real_poi_count": len(dataset.pois),
        "real_walking_snapshot": network.metadata["snapshot_id"],
        "start_kind": "fixed_public_dataset_center_and_stored_public_poi",
        "public_start_poi_ids": [target], "user_coordinates_used": False,
        "environment_file_loaded": False, "paid_llm_calls": 0, "provider_weather_calls": 0,
        "external_http_attempts": len(network_attempts),
        "passed": all(c["passed"] for c in checks) and not network_attempts,
        "passed_count": sum(c["passed"] for c in checks), "case_count": len(checks), "checks": checks,
        "limitations": [
            "Integration assertions use injected synthetic weather and cannot establish live provider availability.",
            "Indoor tags do not prove heating, current opening, accessible entrances, or covered outdoor walks.",
            "OSM paths and approximate connectors do not establish current safety or absence of closures.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "climate-verification.json")
    args = parser.parse_args()
    report = verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for check in report["checks"]:
        print(("PASS " if check["passed"] else "FAIL ") + check["name"])
        if not check["passed"]:
            print(check["error"])
    print(f"{report['passed_count']}/{report['case_count']} cases passed; external HTTP attempts: {report['external_http_attempts']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
