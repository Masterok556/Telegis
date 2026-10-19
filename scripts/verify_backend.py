"""Run acceptance scenarios on the REAL saved dataset, without paid model calls.

python scripts/verify_backend.py
Writes docs/verification.json, docs/api-example.json, docs/openapi.json and
docs/test-scenarios.md. The bundled dataset contains public POI, never user GPS.
"""
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def main() -> int:
    settings = replace(Settings.from_env(), llm_api_key="", llm_model="")
    app = create_app(settings)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    checks = []
    with TestClient(app) as client:
        health = client.get("/api/health")
        if health.status_code != 200:
            print("FAIL: нет рабочего датасета. Запустите scripts/collect_pois.py.")
            return 1
        metadata = client.get("/api/meta").json()
        location = client.get("/api/locations").json()["locations"][0]
        base = {"query": "Хочу погулять", "lat": location["lat"], "lon": location["lon"], "available_minutes": 60, "category": "walk"}
        dataset = app.state.store.get()
        ids = {p.poi_id for p in dataset.pois}

        def run(name, overrides, predicate, expectation):
            response = client.post("/api/recommend", json=base | overrides)
            body = response.json()
            passed = response.status_code == 200 and predicate(body)
            rows = body.get("recommendations", [])
            passed = passed and all(r["poi_id"] in ids and r["total_minutes_estimate"] <= (base | overrides)["available_minutes"] for r in rows)
            checks.append({"name": name, "expected": expectation, "passed": passed,
                           "status_code": response.status_code, "count": len(rows), "mode": body.get("mode"),
                           "names": [r["name"] for r in rows], "message": body.get("message", "")})
            return body

        sixty = run("Прогулка, 60 минут", {}, lambda b: 1 <= len(b["recommendations"]) <= 3,
                    "1–3 реальных места; общий бюджет каждого ≤60 минут")
        twenty = run("Прогулка, 20 минут", {"available_minutes": 20},
                     lambda b: all(r["total_minutes_estimate"] <= 20 for r in b["recommendations"]),
                     "Только варианты ≤20 минут либо честная пустая выдача")
        checks.append({"name": "Адаптация бюджета 60 → 20", "expected": "Набор рекомендаций изменился",
                       "passed": {p["poi_id"] for p in sixty["recommendations"]} != {p["poi_id"] for p in twenty["recommendations"]}})
        coffee = run("Кофе рядом", {"category": "cafe", "query": "Хочу кофе рядом"},
                     lambda b: bool(b["recommendations"]) and all(r["category"] == "cafe" for r in b["recommendations"]),
                     "1–3 кафе из датасета")
        run("Розетка и тишина", {"category": "cafe", "query": "Хочу тихое кафе с розеткой"},
            lambda b: b["recommendations"] == [] and bool(b["message"]),
            "Нет подтверждений в текущих данных — пустая выдача с объяснением")
        run("Недостаточно времени на музей", {"available_minutes": 10, "query": "Хочу музей"},
            lambda b: b["recommendations"] == [] and bool(b["message"]), "Не предлагать посещение, которое не помещается в бюджет")
        run("За пределами района", {"lat": 43.238, "lon": 76.945},
            lambda b: b["recommendations"] == [] and "покрытия" in b["message"], "Объяснить ограничение зоны")
        run("Открыто сейчас", {"category": "cafe", "query": "Нужно кафе открыто сейчас"},
            lambda b: b["recommendations"] == [] and bool(b["message"]), "Не обещать текущую доступность")
        rows = sixty["recommendations"] + coffee["recommendations"]
        unknown = [r for r in rows if r["opening_hours"] is None]
        checks.append({"name": "Неизвестные часы", "expected": "В карточках без расписания есть предупреждение",
                       "passed": bool(unknown) and all(any("Часы работы не подтверждены" in w for w in r["warnings"]) for r in unknown),
                       "count": len(unknown)})
        checks.append({"name": "Источник и идентичность POI", "expected": "Все показанные ID/названия/координаты взяты из датасета",
                       "passed": all(any(p.poi_id == r["poi_id"] and p.name == r["name"] and p.lat == r["lat"] and p.lon == r["lon"] and p.source_url == r["source_url"] for p in dataset.pois) for r in rows)})
        report = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "metadata": metadata,
                  "starting_location": location, "model_test": "Live LLM not exercised; acceptance scenarios explicitly use fallback. Mocked RAG/provider errors are covered by pytest.",
                  "checks": checks, "passed": all(c["passed"] for c in checks)}
        (docs / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (docs / "api-example.json").write_text(json.dumps({"request": base, "response": sixty}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (docs / "openapi.json").write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Тестовые сценарии и ограничения", "", f"Проверено: {report['checked_at']}.",
             f"Датасет: {metadata['poi_count']} реальных POI, снимок `{metadata['snapshot_id']}`.",
             f"Стартовая точка: {location['name']} (координаты из OSM).", "",
             "Проверки ниже выполнены на сохранённом реальном датасете через FastAPI TestClient. Для воспроизводимости модель отключена: режим fallback.", "",
             "| Сценарий | Ожидание | Фактический результат |", "|---|---|---|"]
    for c in checks:
        actual = ("PASS" if c["passed"] else "FAIL") + (f"; {c['count']} рекомендаций/карточек" if "count" in c else "")
        if c.get("names"):
            actual += "; " + ", ".join(c["names"])
        lines.append(f"| {c['name']} | {c['expected']} | {actual} |")
    lines += ["", "## Ограничения", "",
              "- Покрытие: круг 3,5 км около EXPO / Mega Silk Way. Радиус отбора от пользователя — до 2,5 км; датасет не исчерпывающий.",
              "- distance_m — по прямой. При доступной сети OSM время обычной рекомендации вычисляется по более длинному пути туда/обратно со скоростью 70 м/мин и запасом на ориентирование. Без сети используется явно помеченная эвристика 1,3 × расстояние. Это не гарантия успеть.",
              "- Время посещения задаётся по категории. Очереди, погода, светофоры, билеты, реальный вход и ограничения доступа не моделируются.",
              "- Центры площадных объектов могут отличаться от входов. Дата сбора не означает проверку актуальности каждого поля.",
              "- Нет подтверждения «открыто сейчас». Расписания показываются как сведения источника; часовой пояс расписаний — местный, их вычисление не реализовано.",
              "- Розетки, Wi-Fi, тишина и доступность допускаются только при явной поддержке в данных. Отсутствие тега — неизвестность.",
              "- Ночные активности, аэропорт, цены, интерактивность и другие неподтверждённые условия не обещаются. Произвольный язык понимается неполно: доступны лексический поиск и явно перечисленные правила.",
              "- RAG использует BM25 по POI и подтверждаемым фактам, а не эмбеддинги. LLM выбирает ID, причины и занятия из разрешённых вариантов; проверяемый текст собирает сервер. Мини-маршрут рассчитывается локально без LLM.",
              "- Сбой/отсутствие модели явно обозначается fallback. Эта воспроизводимая проверка отключает модель. Отдельные результаты реальных вызовов OpenRouter: `live-rag-walk.json` и `live-rag-cafe.json`; их дата относится только к конкретному прогону.",
              "- Нет хранения пользовательских координат/запросов и аналитики. Точный GPS и исходный запрос модели не передаются. При публичном размещении дополнительно настройте журналы прокси/хостинга.",
              "- Прототип для хакатона: нет авторизации и ограничения частоты запросов; публичный сервер может расходовать средства API. Не публикуйте его с ключом без соответствующей защиты.",
              "", "## Источники", "",
              "Данные © OpenStreetMap contributors, ODbL 1.0: https://www.openstreetmap.org/copyright . Ссылки на конкретные объекты находятся в каждой записи.", "",
              "Автоматические проверки схемы, ошибок модели, отсутствия выдуманных ID, неизвестных свойств и атомарного обновления: `python -m pytest -q`.",
              "Подробный машинный отчёт: `verification.json`. Пример настоящего ответа для интерфейса: `api-example.json`."]
    (docs / "test-scenarios.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["passed"] else "FAIL ") + c["name"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
