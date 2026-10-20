"""Check real family/night/tourist scenarios without LLM calls or real user GPS.

Uses public POI coordinates from the delivered dataset as test starting points.
Writes evidence to docs/expanded-scenarios.json and docs/expanded-scenarios-report.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.config import Settings
from app.data_store import DataStore
from app.facts import excluded_from_routes, facts_for
from app.geo import distance_m
from app.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    dataset = DataStore(ROOT / "data").get()
    known = {poi.poi_id: poi for poi in dataset.pois}
    origin = dataset.locations[0]
    coords = {"lat": origin.lat, "lon": origin.lon}
    checks, cases = [], []

    def check(case_id, name, condition, detail=""):
        checks.append({"case": case_id, "check": name, "passed": bool(condition), "detail": detail})

    def compact(body):
        # Geometry has been checked in memory. The report keeps sufficient
        # identifiers/timing/source evidence without repeating thousands of vertices.
        result = dict(body)
        if "route_coordinates" in result:
            result["route_vertex_count"] = len(result.pop("route_coordinates"))
        if "legs" in result:
            result["legs"] = [{k: v for k, v in leg.items() if k != "coordinates"}
                              | {"vertex_count": len(leg.get("coordinates", []))}
                              for leg in result["legs"]]
        return result

    with TestClient(create_app(Settings(llm_api_key="", llm_model=""))) as client:
        meta_response = client.get("/api/meta")
        check("dataset", "Dataset API is available", meta_response.status_code == 200)
        meta = meta_response.json()

        def run(case_id, query, *, mode="recommend", category="walk", minutes=120,
                include_coffee=False, start=None, expected="any", allowed=None,
                effective=None, radius=None, night=False):
            request = (start or coords) | {"query": query, "available_minutes": minutes}
            request |= {"category": category} if mode == "recommend" else {"include_coffee": include_coffee}
            started = time.monotonic()
            response = client.post(f"/api/{mode}", json=request)
            elapsed = round(time.monotonic() - started, 4)
            check(case_id, "HTTP 200", response.status_code == 200, str(response.status_code))
            body = response.json()
            cases.append({"id": case_id, "endpoint": f"/api/{mode}", "request": request,
                          "elapsed_seconds": elapsed, "response": compact(body)})
            if response.status_code != 200:
                return body
            places = body.get("recommendations", body.get("stops", []))
            context = body.get("used_context", {})
            effective_budget = context.get("effective_minutes", minutes)
            check(case_id, "Form budget is never increased", effective_budget <= minutes)
            if effective is not None:
                check(case_id, "Text time limit respected", effective_budget == effective,
                      f"effective_minutes={effective_budget}")
            if expected == "nonempty":
                check(case_id, "At least one grounded result", bool(places), body.get("message", ""))
            if expected == "empty":
                check(case_id, "Unsupported condition is not silently dropped", not places, body.get("message", ""))
                check(case_id, "Refusal is explained", bool(body.get("message")))
            check(case_id, "At most three distinct places",
                  len(places) <= 3 and len({p["poi_id"] for p in places}) == len(places))
            for place in places:
                poi = known.get(place["poi_id"])
                check(case_id, f"Known sourced POI: {place['name']}", poi is not None)
                if poi is None:
                    continue
                check(case_id, f"No held project: {place['name']}", not excluded_from_routes(poi))
                check(case_id, f"Canonical source: {place['name']}", place.get("source_url") == poi.source_url)
                check(case_id, f"Coordinates match source: {place['name']}",
                      place.get("lat") == poi.lat and place.get("lon") == poi.lon)
                check(case_id, f"Hours are not invented: {place['name']}", place.get("opening_hours") == poi.opening_hours)
                check(case_id, f"Why and activity present: {place['name']}",
                      bool(place.get("why")) and bool(place.get("activity")))
                check(case_id, f"Activity marked as idea: {place['name']}",
                      place.get("activity_source") == "suggested_idea")
                check(case_id, f"Warnings supplied: {place['name']}", bool(place.get("warnings")))
                if allowed:
                    check(case_id, f"Required category: {place['name']}", poi.category in allowed)
                if radius is not None:
                    meters = distance_m(request["lat"], request["lon"], poi.lat, poi.lon)
                    check(case_id, f"Radius respected: {place['name']}", meters <= radius + 1)
                if night:
                    qualifies = poi.opening_hours == "24/7" or any(
                        fact["id"] == "official_hours_24_7" and fact["kind"] == "official"
                        for fact in facts_for(poi)) or (
                        poi.tags.get("lit") == "yes" and poi.category not in {"cafe", "museum", "mall", "gallery"})
                    check(case_id, f"Positive night source property: {place['name']}", qualifies)
                    text = " ".join([place.get("why", ""), place.get("activity", ""), *place.get("warnings", [])]).lower()
                    check(case_id, f"Night uncertainty visible: {place['name']}",
                          bool(re.search(r"ноч|освещ|24/7", text)))
                official = {fact["id"]: fact for fact in facts_for(poi)}
                if case_id == "child_interactive":
                    check(case_id, f"Interactive experience has source evidence: {place['name']}",
                          any(e.get("kind") == "official" and re.search(r"интерактив|interactive", e.get("text", ""), re.I)
                              for e in place.get("evidence", [])))
                if (case_id.startswith("child") or case_id == "children_en") and poi.category == "mall":
                    check(case_id, f"Mall family activity has source evidence: {place['name']}",
                          any(e.get("kind") == "official" and re.search(r"дет|семейн|кино|каток|развлеч|cinema|family|skating",
                                                                      e.get("text", ""), re.I)
                              for e in place.get("evidence", [])))
                for evidence in place.get("evidence", []):
                    fact = official.get(evidence["id"])
                    check(case_id, f"Evidence from stored source: {evidence['id']}",
                          fact is not None and fact["text"] == evidence["text"]
                          and fact["source_url"] == evidence["source_url"])
                if mode == "recommend":
                    check(case_id, f"Return and visit fit time: {place['name']}",
                          place["total_minutes_estimate"] == 2 * place["walk_minutes_estimate"] + place["visit_minutes_estimate"]
                          <= effective_budget)
                    check(case_id, f"No negative remaining time: {place['name']}",
                          place.get("time_margin_minutes", 0) >= 0)
            if mode == "itinerary" and body.get("status") == "ready":
                check(case_id, "At least two route stops", len(places) >= 2)
                legs = body.get("legs", [])
                check(case_id, "Every stop and return has a leg", len(legs) == len(places) + 1)
                check(case_id, "Return to starting point", bool(legs) and legs[-1]["to_id"] == "start")
                check(case_id, "Full time equation",
                      body["total_minutes_estimate"] == body["walking_minutes_estimate"]
                      + body["visit_minutes_estimate"] + body["reserve_minutes"] <= effective_budget)
                check(case_id, "Positive reserve", body["reserve_minutes"] >= 5)
                check(case_id, "Each route leg has actual geometry",
                      all(len(leg.get("coordinates", [])) >= 2 for leg in legs))
                check(case_id, "No fake straight-line route kind",
                      all(leg["route_kind"] == "osm_walking_graph_with_approximate_connectors" for leg in legs))
                geometry = body.get("route_coordinates", [])
                if geometry:
                    start_coords = [request["lon"], request["lat"]]
                    check(case_id, "Geometry starts and ends at chosen start",
                          geometry[0] == start_coords and geometry[-1] == start_coords)
                check(case_id, "Coffee option respected",
                      sum(p["category"] == "cafe" for p in places) == (1 if include_coffee else 0))
            return body

        # Existing scenarios remain useful after adding new intents.
        walk_categories = {"attraction", "monument", "memorial", "artwork", "museum", "gallery", "garden", "park", "viewpoint"}
        run("legacy_walk", "Хочу погулять", minutes=60, expected="nonempty", allowed=walk_categories)
        run("legacy_coffee", "Кофе", category="cafe", minutes=60, expected="nonempty", allowed={"cafe"})
        run("legacy_japanese", "Хочу японский сад с камнями", expected="nonempty", allowed={"garden"})
        run("legacy_sockets", "Кофе и тихое место с розеткой", category="cafe", expected="empty")
        run("legacy_120_route", "Хочу погулять", mode="itinerary", include_coffee=True,
            expected="nonempty", allowed=walk_categories | {"cafe"})
        tight = run("legacy_60_route", "Хочу погулять", mode="itinerary", include_coffee=True, minutes=60)
        suggested = tight.get("suggested_minimum_minutes")
        if suggested:
            run("suggested_budget", "Хочу погулять", mode="itinerary", include_coffee=True,
                minutes=suggested, expected="nonempty")

        run("child_walk", "Хочу погулять с ребёнком", expected="nonempty",
            allowed={"park", "garden", "playground", "mall"})
        run("child_playground", "С ребёнком 3 лет хочу на детскую площадку", expected="nonempty",
            allowed={"playground"})
        run("child_interactive", "С ребёнком хочу в музей с интерактивами", allowed={"museum"})
        run("child_stroller", "С детской коляской хочу прогулку без лестниц", expected="empty")
        run("child_stroller_route", "Прогулка с коляской без лестниц", mode="itinerary", expected="empty")
        run("child_radius_time", "Прогулка с ребёнком не дальше 300 м на 30 минут",
            effective=30, radius=300, allowed={"park", "garden", "playground", "mall"})
        run("child_play_cafe", "Кафе с детской игровой зоной", category="cafe", expected="empty")
        run("child_allergy", "Кафе для ребёнка с аллергией на орехи", category="cafe", expected="empty")
        run("child_route", "Хочу погулять с ребёнком", mode="itinerary", minutes=180,
            expected="nonempty", allowed={"park", "garden", "playground", "mall"})
        run("children_en", "A walk with kids", expected="nonempty",
            allowed={"park", "garden", "playground", "mall"})

        run("night_walk", "Ночная прогулка", night=True)
        run("night_walk_en", "Night walk", night=True)
        official_night = next((p for p in dataset.pois if p.category != "cafe" and any(
            fact["id"] == "official_hours_24_7" for fact in facts_for(p))), None)
        if official_night:
            run("night_landmark_nearby", "Ночная прогулка", minutes=60, night=True,
                start={"lat": official_night.lat, "lon": official_night.lon}, expected="nonempty")
        run("night_museum", "Хочу ночью в музей", expected="empty")
        run("night_cafe", "Кофе ночью", category="cafe", minutes=180, night=True)
        all_night = next((p for p in dataset.pois if p.category == "cafe" and p.opening_hours == "24/7"), None)
        if all_night:
            run("night_cafe_nearby", "Кофе ночью", category="cafe", minutes=60, night=True,
                start={"lat": all_night.lat, "lon": all_night.lon}, expected="nonempty")
        run("night_route", "Ночная прогулка", mode="itinerary", minutes=180, night=True)
        run("night_negated", "Ночная прогулка не нужна, хочу дневную", expected="nonempty")
        run("open_now", "Только места, которые точно открыты сейчас", expected="empty")

        tourist_categories = {"attraction", "monument", "memorial", "artwork", "museum", "gallery", "garden", "park", "viewpoint"}
        run("tourist_intro", "Я турист, впервые в Астане, что посмотреть на 2 часа?",
            expected="nonempty", allowed=tourist_categories)
        run("tourist_30_ru", "Я турист, у меня 30 минут", effective=30, allowed=tourist_categories)
        run("tourist_30_en", "I am a tourist, I have 30 minutes for sightseeing",
            effective=30, allowed=tourist_categories)
        run("tourist_route", "Я турист, хочу увидеть достопримечательности", mode="itinerary",
            minutes=180, allowed=tourist_categories, expected="nonempty")
        run("tourist_airport", "Я турист, два часа перед вылетом", expected="empty")
        run("tourist_airport_en", "I have two hours before my flight", expected="empty")
        run("airport_route", "Я турист, два часа перед вылетом", mode="itinerary", expected="empty")
        run("out_of_coverage", "Хочу погулять с ребёнком", start={"lat": 43.238, "lon": 76.945}, expected="empty")
        run("very_short_route", "Хочу погулять с ребёнком", mode="itinerary", minutes=15, expected="empty")

        for mode in ("recommend", "itinerary"):
            payload = coords | {"query": "Хочу погулять", "available_minutes": 0}
            payload |= {"category": "walk"} if mode == "recommend" else {"include_coffee": False}
            check("validation", f"{mode}: invalid time rejected", client.post(f"/api/{mode}", json=payload).status_code == 422)

    passed = all(check["passed"] for check in checks)
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
        "paid_llm_calls": 0, "mode": "TestClient + deterministic fallback",
        "snapshot_id": dataset.manifest["snapshot_id"], "poi_count": len(dataset.pois),
        "data_quality": meta.get("data_quality"), "walking_network": meta.get("walking_network"),
        "scenario_count": len(cases), "check_count": len(checks),
        "scenarios_passed": sum(all(check["passed"] for check in checks if check["case"] == case["id"])
                                for case in cases),
        "passed_count": sum(check["passed"] for check in checks),
        "checks": checks, "cases": cases,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "expanded-scenarios.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = [
        "# Расширенные сценарии Telegis", "",
        f"Проверка: {report['checked_at']}. Снимок: `{report['snapshot_id']}`.",
        f"Результат: **{report['scenarios_passed']}/{report['scenario_count']} сценариев**, "
        f"{report['passed_count']}/{report['check_count']} отдельных проверок.",
        "Проверки выполнены через настоящий FastAPI TestClient на поставляемых данных, без платных вызовов модели.",
        "Стартовые координаты — публичные точки из датасета. Браузер и работа внешнего LLM этим отчётом не проверяются.",
        "", "| Сценарий | Результат | Места | Время, мин |", "|---|---|---|---|",
    ]
    for case in cases:
        body = case["response"]
        places = body.get("recommendations", body.get("stops", []))
        case_passed = all(check["passed"] for check in checks if check["case"] == case["id"])
        names = "; ".join(p["name"] for p in places) or "Честный отказ / нет подходящих данных"
        duration = str(body.get("total_minutes_estimate", "")) if "stops" in body else ", ".join(
            str(p["total_minutes_estimate"]) for p in places)
        markdown.append(f"| {case['id']} | {'PASS' if case_passed else 'FAIL'} | {names.replace('|', '/')} | {duration} |")
    failures = [check for check in checks if not check["passed"]]
    markdown.extend(["", "## Ограничения", "",
        "- Наличие 24/7 или освещения в источнике не подтверждает доступность сейчас и освещение всего пути.",
        "- Безбарьерность всего маршрута, детские игровые зоны кафе и аллергенная безопасность не предполагаются без доказательств.",
        "- Туристические сценарии ограничены покрытием снимка; поездка в аэропорт не рассчитывается.",
        "- Время посещения и ходьбы — оценки. Условия, часы и проходы необходимо уточнять на месте.",
        "", "## Непрошедшие проверки", ""])
    markdown.extend([f"- {item['case']}: {item['check']}. {item['detail']}" for item in failures] or ["Не обнаружены."])
    (args.output_dir / "expanded-scenarios-report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(f"{report['scenarios_passed']}/{len(cases)} scenarios; {report['passed_count']}/{report['check_count']} checks; paid LLM calls: 0.")
    for item in failures:
        print("FAIL", item["case"], item["check"], item["detail"])
    return 0 if passed else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
