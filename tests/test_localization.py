"""Translation may change presentation, never source identity or constraints."""
from copy import deepcopy
from pathlib import Path

import pytest

from app.catalog import place_card, place_info
from app.climate import climate_context
from app.data_store import DataStore
from app.generation import activities_for, evidence_for
from app.localization import localize_response, translate_text
from app.retrieval import Candidate, VISIT_MINUTES
from app.weather import demo_snapshot


ROOT = Path(__file__).resolve().parents[1]
MARKERS = ("[Original source text]", "[Дереккөз мәтіні: түпнұсқа]")


@pytest.mark.parametrize("locale", ["en", "kz"])
def test_dynamic_budget_reason_and_activity_preserve_numbers_and_uncertainty(locale):
    original = {
        "why": "По данным OpenStreetMap это кафе. Около 47 мин с возвращением: 15 мин на месте и примерно по 16 мин в каждую сторону.",
        "activity": "Если заведение доступно, возьмите кофе и сделайте перерыв примерно на 15 мин; меню и цены уточните на месте.",
        "warnings": ["Часы работы не подтверждены."],
        "opening_hours": "Mo-Su 09:00-21:00",
        "available_minutes": 60,
    }
    result = localize_response(original, locale)
    assert result["why"] != original["why"] and not any(m in str(result) for m in MARKERS)
    assert all(str(n) in result["why"] for n in (47, 15, 16))
    assert "15" in result["activity"]
    assert result["opening_hours"] == original["opening_hours"]
    assert result["available_minutes"] == 60
    assert result["warnings"][0] == (
        "Opening hours are unconfirmed." if locale == "en" else "Жұмыс уақыты расталмаған."
    )
    assert ("If the café is accessible" if locale == "en" else "Кафе қолжетімді болса") in result["activity"]


@pytest.mark.parametrize("locale", ["en", "kz", "ru"])
def test_response_is_copy_and_keeps_identity_source_dates_enums_and_geometry(locale):
    payload = {
        "name": "Сад камней", "from_name": "Кафе «Коктем»", "to_name": "Ботанический сад",
        "poi_id": "osm_way_123", "source_url": "https://example.org/страница?q=1",
        "website": "https://example.org", "phone": "+7 7172 000000",
        "opening_hours": "Mo-Su 10:00-22:00", "category": "cafe", "mode": "fallback",
        "collected_at": "2026-10-20T12:00:00Z", "coordinates": [[51.089, 71.419], [51.09, 71.42]],
        "tags": {"name": "Название", "description": "Исходное описание OSM"},
        "evidence": [{"id": "osm_indoor", "text": "В OSM отмечены места внутри помещения.",
                      "source_url": "https://www.openstreetmap.org/way/123", "confidence": "source_reported"}],
    }
    before = deepcopy(payload)
    result = localize_response(payload, locale)
    assert payload == before
    for key in set(payload) - {"evidence", "tags"}:
        assert result[key] == payload[key]
    assert result["tags"] == payload["tags"]
    assert result["evidence"][0]["source_url"] == payload["evidence"][0]["source_url"]
    assert result["evidence"][0]["id"] == "osm_indoor"
    result["coordinates"][0][0] = 0
    assert payload["coordinates"][0][0] == 51.089
    if locale == "ru":
        assert result["evidence"] == payload["evidence"]
    else:
        assert result["evidence"][0]["text"] != payload["evidence"][0]["text"]


@pytest.mark.parametrize("locale,prefix", [
    ("en", "[Original source text] "), ("kz", "[Дереккөз мәтіні: түпнұсқа] "),
])
def test_unknown_source_is_visible_and_labeled_without_invented_translation(locale, prefix):
    source = "Неизвестный автор указал экспериментальную деталь 22.05.2026: 5.5 м."
    result = localize_response({"description": source, "source_url": "https://example.org/source"}, locale)
    assert result["description"] == prefix + source
    assert result["source_url"] == "https://example.org/source"
    assert translate_text(result["description"], locale) == result["description"]


@pytest.mark.parametrize("locale", ["en", "kz"])
def test_current_shipped_catalog_all_activity_templates_and_grounded_reasons_are_translated(locale):
    """Catch real source/renderer gaps, including arch/garden and unnamed playgrounds."""
    dataset = DataStore(ROOT / "data").get()
    seen_activities = set()
    for poi in dataset.pois:
        candidate = Candidate(poi, 427, 8, VISIT_MINUTES.get(poi.category, 15), 46, 0)
        activities = activities_for(candidate)
        seen_activities.update(activities)
        card = place_card(poi)
        info = place_info(poi)
        values = [*activities.values(), *evidence_for(candidate, ()).values(),
                  card.description, *card.warnings, *(f.text for f in card.evidence), info.tip]
        for text in values:
            localized = translate_text(text, locale)
            assert not any(marker in localized for marker in MARKERS), (poi.poi_id, text, localized)
    assert {"arch_details", "stone_observation", "themed_garden_walk", "family_play"} <= seen_activities


@pytest.mark.parametrize("locale", ["en", "kz"])
def test_route_totals_translate_without_changing_category_order_or_budget(locale):
    payload = {"why": "парк → кафе: 3 разных места, 29 мин на все переходы включая возвращение, 50 мин на остановки и 6 мин запаса. Итого примерно 85 из 90 мин.",
               "walking_minutes_estimate": 29, "visit_minutes_estimate": 50,
               "reserve_minutes": 6, "total_minutes_estimate": 85}
    result = localize_response(payload, locale)
    assert not any(marker in result["why"] for marker in MARKERS)
    assert ("park → café" if locale == "en" else "саябақ → кафе") in result["why"]
    assert all(str(n) in result["why"] for n in [3, 29, 50, 6, 85, 90])
    assert {k: v for k, v in result.items() if k != "why"} == {k: v for k, v in payload.items() if k != "why"}


@pytest.mark.parametrize("locale", ["en", "kz"])
def test_weather_and_climate_text_localized_but_demo_cannot_become_current(locale):
    snapshot = demo_snapshot()
    payload = climate_context(True, snapshot).model_dump(mode="json")
    result = localize_response(payload, locale)
    assert result["policy"] == "paused" and result["applied"] is False
    assert result["weather"]["status"] == "demo"
    assert result["weather"]["valid_at"] is None and result["weather"]["fetched_at"] is None
    assert result["weather"]["current"] == payload["weather"]["current"]
    assert result["weather"]["policy"]["mode"] == payload["weather"]["policy"]["mode"]
    assert result["reason_codes"] == ["weather_not_current"]
    assert result["weather"]["source"] == payload["weather"]["source"]
    for text in [result["message"], result["weather"]["policy"]["message"], *result["weather"]["warnings"]]:
        assert not any(marker in text for marker in MARKERS)
    assert ("synthetic weather" if locale == "en" else "Ойдан алынған ауа райы") in result["weather"]["warnings"][0]


def test_unsupported_locale_fails_explicitly():
    with pytest.raises(ValueError, match="Unsupported locale"):
        localize_response({"message": "Часы работы не подтверждены."}, "de")
