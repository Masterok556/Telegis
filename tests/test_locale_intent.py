"""Localized quick actions must preserve constraints, not just translate labels."""
from pathlib import Path

import pytest

from app.data_store import DataStore
from app.models import RecommendRequest
from app.retrieval import retrieve, required_features, explicit_limits
from app.scenarios import scenario_flags, scenario_rejection
from app.climate import requires_indoor


@pytest.mark.parametrize("text,flag", [
    ("Баламен серуен", "family"), ("Түнде серуен", "night"),
    ("Мен туристпін", "tourist"),
    ("A family walk with children", "family"), ("A night walk", "night"),
])
def test_quick_actions_have_intent(text, flag):
    assert flag in scenario_flags(text)


@pytest.mark.parametrize("text,feature", [
    ("тыныш орын", "quiet"), ("Розеткасы бар кафе", "socket"),
    ("Wi-Fi бар кофе", "wifi"), ("мүгедектер үшін", "wheelchair"),
])
def test_kazakh_features_are_required_not_ignored(text, feature):
    assert feature in required_features(text)


def test_kazakh_waived_feature_and_time_limit():
    assert required_features("тыныштық қажет емес") == ()
    assert explicit_limits("30 минут серуендегім келеді", 120)[0] == 30
    assert explicit_limits("Мен туристпін 1 сағат бар", 120)[0] == 60


@pytest.mark.parametrize("text", [
    "Не в помещении, хочу погулять снаружи", "Не хочу в помещении",
    "Жабық орын қажет емес, саябақта серуен", "Жабық орын керек емес",
    "No indoor places",
])
def test_waived_indoor_preference_does_not_exclude_outdoor_places(text):
    assert not requires_indoor(text)


def test_waived_kazakh_night_preference_is_not_night():
    assert "night" not in scenario_flags("Түнде емес, күндіз серуен")
    assert "night" not in scenario_flags("Түнгі серуен қажет емес")


@pytest.mark.parametrize("text", ["қазір ашық кафе", "әуежайға барамын", "арбамен серуен", "тегін мұражай"])
def test_unverified_kazakh_conditions_are_not_silently_dropped(text):
    assert scenario_rejection(text)


def test_kazakh_family_night_quiet_search_apply_to_real_data():
    dataset = DataStore(Path(__file__).resolve().parents[1] / "data").get()
    origin = dataset.locations[0]
    base = dict(lat=origin.lat, lon=origin.lon, available_minutes=120, locale="kz")
    family = retrieve(RecommendRequest(query="Баламен серуен", category="walk", **base), dataset)
    assert family.candidates
    assert all(c.poi.category in {"park", "garden", "playground"} for c in family.candidates)
    quiet = retrieve(RecommendRequest(query="тыныш орын", category="cafe", **base), dataset)
    assert not quiet.candidates and quiet.required_features == ("quiet",)
    night = retrieve(RecommendRequest(query="Түнде серуен", category="walk", **base), dataset)
    assert all("night" in c.scenarios for c in night.candidates)
    walk = retrieve(RecommendRequest(query="Саябақта серуендегім келеді", category="walk", **base), dataset)
    assert walk.candidates and all(c.poi.category in {"park", "garden"} for c in walk.candidates)
