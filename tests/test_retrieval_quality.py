"""Regression scenarios for user intent; every POI here is a synthetic fixture."""
import pytest

from app.data_store import Dataset
from app.models import POI, RecommendRequest
from app.retrieval import explicit_limits, required_features, retrieve


@pytest.fixture
def quality_dataset():
    categories = ["artwork", "park", "garden", "museum", "cafe", "cafe", "playground", "memorial"]
    offsets = [0, 0.001, 0.003, 0.002, 0.001, 0.004, 0.003, 0.0005]
    return Dataset(pois=tuple(POI(
        poi_id=f"osm_node_{index}", name=f"Synthetic {category} {index}",
        lat=51.089 + offset, lon=71.419, category=category, description="Test fixture only",
        tags={}, opening_hours=None, source_url=f"https://www.openstreetmap.org/node/{index}",
        collected_at="2026-10-19T00:00:00+00:00", coordinate_kind="point",
        confirmed_features={"wifi": index == 6, "socket": None, "quiet": None, "wheelchair": None},
    ) for index, (category, offset) in enumerate(zip(categories, offsets), start=1)), locations=(),
        manifest={"coverage": {"lat": 51.089, "lon": 71.419, "radius_m": 3500}})


def search(dataset, query, category="walk", minutes=90):
    return retrieve(RecommendRequest(query=query, lat=51.089, lon=71.419,
                                    category=category, available_minutes=minutes), dataset)


def categories(result):
    return {candidate.poi.category for candidate in result.candidates}


def test_solo_walk_does_not_match_night_constraint(quality_dataset):
    assert search(quality_dataset, "Хочу погулять в одиночку").candidates
    assert not search(quality_dataset, "Хочу ночную прогулку").candidates


@pytest.mark.parametrize("query", ["Бюджет времени 60 минут, хочу погулять", "Бюджет 60 минут, хочу в парк"])
def test_time_budget_is_not_a_price_constraint(quality_dataset, query):
    assert search(quality_dataset, query).candidates


@pytest.mark.parametrize("query", ["Бюджет до 1000", "Хочу кофе до 1000 тенге", "Бюджетное кафе"])
def test_price_constraints_remain_explicitly_unsupported(quality_dataset, query):
    result = search(quality_dataset, query, "cafe")
    assert not result.candidates
    assert "недостаточно сведений" in result.message


@pytest.mark.parametrize("query", ["Не хочу в музей", "Без музеев и кафе", "Музеи не интересуют"])
def test_excluded_categories_are_not_interests(quality_dataset, query):
    result = search(quality_dataset, query)
    assert result.candidates
    assert "museum" not in categories(result)


def test_positive_interest_wins_over_unrelated_negated_category(quality_dataset):
    assert categories(search(quality_dataset, "Не музей, хочу в парк")) == {"park", "garden"}


@pytest.mark.parametrize("query", ["Хочу кофе возле музея", "Я сейчас в музее, хочу кофе", "Кафе около парка"])
def test_nearby_landmark_does_not_become_the_requested_activity(quality_dataset, query):
    assert categories(search(quality_dataset, query, "cafe")) == {"cafe"}


def test_child_does_not_override_explicit_museum_intent(quality_dataset):
    assert categories(search(quality_dataset, "Хочу с ребёнком в музей")) == {"museum"}


def test_generic_walk_with_child_uses_public_outdoor_categories(quality_dataset):
    result = search(quality_dataset, "Хочу прогуляться с ребёнком")
    assert categories(result) == {"park", "garden", "playground"}


def test_parking_word_does_not_force_park_category(quality_dataset):
    assert "artwork" in categories(search(quality_dataset, "Я на парковке, хочу погулять"))


@pytest.mark.parametrize("query", [
    "Кофе, интернет не нужен", "Кофе без Wi-Fi и розеток", "Кофе, не обязательно тихое",
    "Coffee, wifi not required", "Кофе, тишина не важна",
])
def test_explicitly_waived_amenities_do_not_empty_results(quality_dataset, query):
    assert required_features(query) == ()
    assert search(quality_dataset, query, "cafe").candidates


def test_waiving_one_feature_keeps_other_required_features(quality_dataset):
    result = search(quality_dataset, "Кофе без розеток, но с Wi-Fi", "cafe")
    assert result.required_features == ("wifi",)
    assert [candidate.poi.poi_id for candidate in result.candidates] == ["osm_node_6"]


@pytest.mark.parametrize("query", ["У меня 20 минут, хочу погулять", "Прогулка на 10–20 минут"])
def test_text_budget_cannot_be_exceeded_by_form_budget(quality_dataset, query):
    result = search(quality_dataset, query, minutes=90)
    assert result.candidates
    assert result.effective_minutes == 20
    assert all(candidate.total_minutes <= 20 for candidate in result.candidates)


def test_long_text_budget_never_increases_form_limit(quality_dataset):
    result = search(quality_dataset, "Хочу погулять на 2 часа", minutes=20)
    assert result.candidates
    assert all(candidate.total_minutes <= 20 for candidate in result.candidates)


@pytest.mark.parametrize("query", ["Хочу погулять не дальше 150 м", "Прогулка в радиусе 0,15 км"])
def test_explicit_radius_filters_farther_places(quality_dataset, query):
    result = search(quality_dataset, query)
    assert result.candidates
    assert result.max_distance_m == 150
    assert all(candidate.distance <= 150 for candidate in result.candidates)
    assert "garden" not in categories(result)


def test_visit_time_is_not_confused_with_distance_limit():
    assert explicit_limits("У меня 1 час, хочу в радиусе 500 м", 90) == (60, 500)


def test_negation_does_not_silently_change_ui_category(quality_dataset):
    result = search(quality_dataset, "Не кафе, хочу в парк", "cafe")
    assert not result.candidates
    assert "расходятся" in result.message
    assert result.excluded_categories == ("cafe",)
