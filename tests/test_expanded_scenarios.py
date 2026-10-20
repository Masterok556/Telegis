"""Behavioural regressions for family, night and tourist intents.

Synthetic places below are deliberately not part of the delivered POI dataset.
The separate verification script exercises the real shipped snapshots.
"""
import pytest

from app.data_store import Dataset
from app.models import POI, RecommendRequest
from app.retrieval import retrieve


@pytest.fixture
def expanded_dataset():
    rows = [
        ("playground", "Synthetic playground", {"leisure": "playground"}, None),
        ("park", "Synthetic lit park", {"leisure": "park", "lit": "yes"}, None),
        ("park", "Synthetic unlit park", {"leisure": "park", "lit": "no"}, None),
        ("park", "Synthetic unknown park", {"leisure": "park"}, None),
        ("cafe", "Synthetic all-night coffee", {"amenity": "cafe"}, "24/7"),
        ("cafe", "Synthetic daytime coffee", {"amenity": "cafe"}, "Mo-Su 10:00-22:00"),
        ("museum", "Synthetic museum, no interactive evidence", {"tourism": "museum"}, None),
        ("artwork", "Synthetic public sculpture", {"tourism": "artwork", "artwork_type": "sculpture"}, None),
        ("mall", "Synthetic mall, no family evidence", {"shop": "mall"}, None),
        ("garden", "Synthetic garden, no visitor facts", {"leisure": "garden"}, None),
    ]
    pois = tuple(POI(
        poi_id=f"osm_node_{990001 + i}", name=name, category=category,
        lat=51.089 + (i + 1) * .0001, lon=71.419,
        description="Synthetic fixture; source properties only.", tags=tags,
        opening_hours=hours, source_url=f"https://www.openstreetmap.org/node/{990001 + i}",
        collected_at="2026-10-20T00:00:00+00:00", coordinate_kind="point",
        confirmed_features={"wifi": None, "socket": None, "quiet": None, "wheelchair": None},
    ) for i, (category, name, tags, hours) in enumerate(rows))
    return Dataset(pois=pois, locations=(), manifest={
        "coverage": {"name": "Synthetic only", "lat": 51.089, "lon": 71.419, "radius_m": 3500}
    })


def search(dataset, query, category="walk", minutes=120):
    return retrieve(RecommendRequest(
        query=query, lat=51.089, lon=71.419,
        category=category, available_minutes=minutes,
    ), dataset)


@pytest.mark.parametrize("query", [
    "Прогулка с ребёнком", "With kids, suggest nearby places", "I am with children, where can we walk?",
])
def test_family_walk_does_not_substitute_art_or_unverified_mall(expanded_dataset, query):
    result = search(expanded_dataset, query)
    assert result.candidates
    assert {candidate.poi.category for candidate in result.candidates} <= {"park", "garden", "playground"}
    assert any(candidate.poi.category == "playground" for candidate in result.candidates)


@pytest.mark.parametrize("query", [
    "С ребёнком хочу в интерактивный музей",
    "Interactive museum for my child",
])
def test_interactive_requirement_needs_actual_evidence(expanded_dataset, query):
    result = search(expanded_dataset, query)
    assert not result.candidates
    assert result.message


@pytest.mark.parametrize("query", [
    "С детской коляской хочу прогулку без лестниц",
    "A stroller accessible walk with no stairs",
    "Хочу парк без ступенек",
])
def test_required_step_free_route_is_not_assumed(expanded_dataset, query):
    result = search(expanded_dataset, query)
    assert not result.candidates
    assert result.message


@pytest.mark.parametrize("query", [
    "Кафе с детской игровой зоной",
    "Cafe with a children's play area",
    "Кафе для ребёнка с аллергией на орехи",
    "Coffee for a child with a nut allergy",
])
def test_specific_family_cafe_requirements_are_not_silently_dropped(expanded_dataset, query):
    result = search(expanded_dataset, query, category="cafe")
    assert not result.candidates
    assert result.message


@pytest.mark.parametrize("query", ["Ночная прогулка", "Night walk"])
def test_night_walk_requires_positive_night_evidence(expanded_dataset, query):
    result = search(expanded_dataset, query)
    assert result.candidates, "A lit outdoor fixture should be available as a caveated option"
    assert all(candidate.poi.tags.get("lit") == "yes" or candidate.poi.opening_hours == "24/7"
               for candidate in result.candidates)


@pytest.mark.parametrize("query", ["Кофе ночью", "Coffee at night"])
def test_night_coffee_does_not_substitute_daytime_cafe(expanded_dataset, query):
    result = search(expanded_dataset, query, category="cafe")
    assert result.candidates
    assert all(candidate.poi.opening_hours == "24/7" for candidate in result.candidates)


@pytest.mark.parametrize("query", ["Ночная прогулка не нужна, хочу дневную", "No night walk, a daytime walk please"])
def test_negated_night_condition_does_not_filter_daytime_options(expanded_dataset, query):
    result = search(expanded_dataset, query)
    assert result.candidates
    assert any(candidate.poi.tags.get("lit") != "yes" for candidate in result.candidates)


@pytest.mark.parametrize("query", [
    "Только места, которые точно открыты сейчас", "Only places open now",
    "Я турист, два часа перед вылетом", "I have two hours before my flight",
])
def test_live_availability_and_airport_constraints_remain_honest(expanded_dataset, query):
    result = search(expanded_dataset, query)
    assert not result.candidates
    assert result.message


@pytest.mark.parametrize("query", [
    "Я турист, у меня 30 минут на прогулку",
    "I am a tourist, I have 30 minutes for sightseeing",
])
def test_tourist_text_time_cannot_be_replaced_by_longer_form_budget(expanded_dataset, query):
    result = search(expanded_dataset, query, minutes=120)
    assert result.effective_minutes == 30
    assert all(candidate.total_minutes <= 30 for candidate in result.candidates)


@pytest.mark.parametrize("query", ["Я турист, впервые в Астане", "I am a tourist, suggest sightseeing"])
def test_tourist_does_not_receive_residential_playground(expanded_dataset, query):
    result = search(expanded_dataset, query)
    assert result.candidates
    assert all(candidate.poi.category not in {"playground", "cafe", "mall"} for candidate in result.candidates)


def test_night_feature_does_not_override_explicit_daytime_category(expanded_dataset):
    result = search(expanded_dataset, "Хочу ночью в музей")
    assert not result.candidates


def test_child_and_time_radius_restrictions_are_joint(expanded_dataset):
    result = search(expanded_dataset, "Прогулка с ребёнком не дальше 100 м на 30 минут")
    assert result.effective_minutes == 30
    assert result.max_distance_m == 100
    assert all(candidate.distance <= 100 and candidate.total_minutes <= 30 for candidate in result.candidates)
    assert all(candidate.poi.category in {"park", "garden", "playground"} for candidate in result.candidates)


def test_generic_adult_walk_does_not_turn_into_a_playground_search(expanded_dataset):
    result = search(expanded_dataset, "Хочу погулять")
    assert result.candidates
    assert all(candidate.poi.category != "playground" for candidate in result.candidates)
