"""Synthetic route fixtures verify promises, not live availability of real places."""
from dataclasses import dataclass
from math import ceil

import pytest
from pydantic import ValidationError

from app.data_store import Dataset
from app.geo import distance_m
from app.itinerary import ItineraryRequest, build_itinerary
from app.models import POI
from app.retrieval import VISIT_MINUTES
from app.walking import WalkingNetwork


START = (51.089, 71.419)


def poi(number, category, lat_offset, lon_offset, **updates):
    return POI(poi_id=f"osm_node_{number}", name=f"Synthetic {category} {number}",
               lat=START[0] + lat_offset, lon=START[1] + lon_offset,
               category=category, description=f"Synthetic test {category}", tags={},
               opening_hours=None, source_url=f"https://www.openstreetmap.org/node/{number}",
               collected_at="2026-10-19T00:00:00+00:00", coordinate_kind="point",
               confirmed_features={"wifi": None, "quiet": None, "socket": None, "wheelchair": None},
               **updates)


@pytest.fixture
def dataset():
    return Dataset(pois=(poi(101, "park", .0009, 0), poi(102, "cafe", 0, .00143),
                         poi(103, "artwork", .0009, .00143), poi(104, "museum", .0018, .00143)),
                   locations=(), manifest={"coverage": {"lat": START[0], "lon": START[1], "radius_m": 3500}})


@dataclass
class TestLeg:
    __test__ = False
    distance_m: int
    coordinates: list[list[float]]
    connector_m: int = 0


class SyntheticNetwork:
    """Only tests use this stub; production requires WalkingNetwork paths."""
    def __init__(self, disconnected=(), multiplier=1.1):
        self.disconnected = set(disconnected)
        self.multiplier = multiplier
        self.calls = []

    def route(self, start, end):
        self.calls.append((start, end))
        if start in self.disconnected or end in self.disconnected:
            return None
        # Include a bend to detect replacement of graph geometry by a direct line.
        return TestLeg(ceil(distance_m(*start, *end) * self.multiplier),
                       [[start[1], start[0]], [(start[1] + end[1]) / 2 + .00005, (start[0] + end[0]) / 2],
                        [end[1], end[0]]])


def request(**updates):
    return ItineraryRequest(lat=START[0], lon=START[1], available_minutes=60, **updates)


def test_circle_accounts_for_every_leg_full_visits_reserve_and_return(dataset):
    network = SyntheticNetwork()
    result = build_itinerary(request(), dataset, network)
    assert result.status == "ready"
    assert len(result.stops) == 3
    assert len({s.category for s in result.stops}) == 3
    assert len(result.legs) == len(result.stops) + 1
    assert result.legs[0].from_id == result.legs[-1].to_id == "start"
    assert result.route_coordinates[0] == result.route_coordinates[-1] == [START[1], START[0]]
    assert result.walking_minutes_estimate == sum(leg.walk_minutes_estimate for leg in result.legs)
    assert result.visit_minutes_estimate == sum(VISIT_MINUTES[s.category] for s in result.stops)
    assert all(s.visit_minutes_estimate == VISIT_MINUTES[s.category] for s in result.stops)
    assert result.reserve_minutes == 6
    assert result.total_minutes_estimate == result.walking_minutes_estimate + result.visit_minutes_estimate + 6
    assert result.total_minutes_estimate <= 60
    assert result.remaining_minutes == 60 - result.total_minutes_estimate
    assert result.distance_m == sum(leg.distance_m for leg in result.legs)
    assert len(result.route_coordinates) > len(result.stops) + 2
    assert len(network.calls) == len(set(network.calls))
    previous_departure = 0
    for leg, stop in zip(result.legs, result.stops):
        assert stop.arrival_minutes_estimate == previous_departure + leg.walk_minutes_estimate
        assert stop.departure_minutes_estimate == stop.arrival_minutes_estimate + stop.visit_minutes_estimate
        assert stop.source_url == f"https://www.openstreetmap.org/node/{stop.poi_id.removeprefix('osm_node_')}"
        assert stop.activity_source == "suggested_idea"
        previous_departure = stop.departure_minutes_estimate
    assert previous_departure + result.legs[-1].walk_minutes_estimate + result.reserve_minutes == result.total_minutes_estimate


def test_tighter_budget_reduces_stops_and_never_shortens_visits(dataset):
    large = build_itinerary(request(), dataset, SyntheticNetwork())
    smaller = build_itinerary(request().model_copy(update={"available_minutes": 40}), dataset, SyntheticNetwork())
    assert large.status == smaller.status == "ready"
    assert len(smaller.stops) == 2 < len(large.stops)
    assert smaller.total_minutes_estimate <= 40
    assert smaller.reserve_minutes == 5
    assert all(s.visit_minutes_estimate == VISIT_MINUTES[s.category] for s in smaller.stops)


def test_insufficient_budget_returns_executable_suggestion_not_fake_short_visit(dataset):
    tiny = request().model_copy(update={"available_minutes": 15})
    result = build_itinerary(tiny, dataset, SyntheticNetwork())
    assert result.status == "no_match" and not result.stops and not result.legs
    assert result.suggested_minimum_minutes is not None and result.suggested_minimum_minutes > 15
    adequate = tiny.model_copy(update={"available_minutes": result.suggested_minimum_minutes})
    assert build_itinerary(adequate, dataset, SyntheticNetwork()).status == "ready"


def test_textual_time_limit_is_stricter_than_form(dataset):
    result = build_itinerary(request(query="Хочу погулять на 20 минут"), dataset, SyntheticNetwork())
    assert result.status == "no_match"
    assert result.used_context.effective_minutes == 20
    assert result.suggested_minimum_minutes > 20


def test_textual_radius_filters_every_stop(dataset):
    result = build_itinerary(request(query="Хочу погулять не дальше 120 метров"), dataset, SyntheticNetwork())
    assert result.status == "ready"
    assert all(distance_m(*START, s.lat, s.lon) <= 120 for s in result.stops)
    assert result.used_context.max_distance_m == 120


def test_park_interest_and_coffee_checkbox_are_combined(dataset):
    result = build_itinerary(request(query="Хочу парк"), dataset, SyntheticNetwork())
    assert result.status == "ready"
    assert {s.category for s in result.stops} == {"park", "cafe"}


@pytest.mark.parametrize("query", ["Хочу прогулку и кофе", "Хочу погулять и выпить кофе",
                                    "Хочу пройтись и кофе", "A walk and coffee", "A stroll and coffee"])
def test_walk_activity_and_coffee_form_a_real_circle(dataset, query):
    result = build_itinerary(request(query=query, include_coffee=True), dataset, SyntheticNetwork())
    assert result.status == "ready"
    assert sum(s.category == "cafe" for s in result.stops) == 1
    assert any(s.category != "cafe" for s in result.stops)
    assert result.legs[0].from_id == result.legs[-1].to_id == "start"
    assert result.total_minutes_estimate <= result.used_context.effective_minutes


@pytest.mark.parametrize("query", ["Хочу кофе без прогулки", "Не хочу погулять, хочу кофе", "Coffee without a walk"])
def test_waived_walk_does_not_turn_coffee_into_a_route(dataset, query):
    result = build_itinerary(request(query=query), dataset, SyntheticNetwork())
    assert result.status == "no_match" and not result.stops


def test_joint_interests_are_both_honored(dataset):
    large = request(query="Хочу парк и музей").model_copy(update={"available_minutes": 120})
    result = build_itinerary(large, dataset, SyntheticNetwork())
    assert result.status == "ready"
    assert {s.category for s in result.stops} == {"park", "museum", "cafe"}
    tight = large.model_copy(update={"available_minutes": 60})
    assert build_itinerary(tight, dataset, SyntheticNetwork()).status == "no_match"


def test_alternative_interests_remain_alternatives(dataset):
    result = build_itinerary(request(query="Хочу парк или музей"), dataset, SyntheticNetwork())
    assert result.status == "ready"
    assert {s.category for s in result.stops} == {"park", "cafe"}


def test_no_coffee_never_selects_a_cafe(dataset):
    result = build_itinerary(request(include_coffee=False, query="Прогулка без кофе и музеев"), dataset, SyntheticNetwork())
    assert result.status == "ready"
    assert {s.category for s in result.stops} == {"park", "artwork"}


@pytest.mark.parametrize("query", ["Прогулка без кофе", "Только парк", "Хочу кофе"])
def test_conflicting_or_single_activity_intent_is_not_silently_relaxed(dataset, query):
    result = build_itinerary(request(query=query), dataset, SyntheticNetwork())
    assert result.status == "no_match" and result.message and not result.stops


def test_missing_graph_does_not_fabricate_a_route(dataset):
    result = build_itinerary(request(), dataset, None)
    assert result.status == "network_unavailable"
    assert not result.stops and not result.legs and not result.route_coordinates


def test_disconnected_coffee_does_not_create_a_straight_line(dataset):
    cafe = next(p for p in dataset.pois if p.category == "cafe")
    result = build_itinerary(request(), dataset, SyntheticNetwork(disconnected=[(cafe.lat, cafe.lon)]))
    assert result.status == "no_match"
    assert not result.route_coordinates and not result.legs and not result.stops
    assert result.suggested_minimum_minutes is None


def test_one_way_graph_requires_actual_return_leg(dataset):
    class NoReturnNetwork(SyntheticNetwork):
        def route(self, start, end):
            return None if end == START else super().route(start, end)

    result = build_itinerary(request(), dataset, NoReturnNetwork())
    assert result.status == "no_match" and not result.legs


def test_long_network_detour_used_instead_of_direct_distance(dataset):
    ordinary = build_itinerary(request(), dataset, SyntheticNetwork())
    detour = build_itinerary(request(), dataset, SyntheticNetwork(multiplier=20))
    assert ordinary.status == "ready"
    assert detour.status == "no_match"
    assert detour.suggested_minimum_minutes > 60


def test_integrates_with_actual_graph_and_preserves_its_vertices(dataset):
    nodes = {0: START} | {i: (p.lat, p.lon) for i, p in enumerate(dataset.pois, 1)}
    pairs = [(0, 1), (1, 3), (3, 2), (2, 0), (3, 4)]
    edges = [(a, b, distance_m(*nodes[a], *nodes[b])) for a, b in pairs + [(b, a) for a, b in pairs]]
    network = WalkingNetwork.from_payload({"nodes": [[i, *p] for i, p in nodes.items()], "edges": edges})
    result = build_itinerary(request(), dataset, network)
    assert result.status == "ready"
    vertices = {(lon, lat) for lat, lon in nodes.values()}
    assert all(tuple(p) in vertices for p in result.route_coordinates)
    assert result.legs[-1].to_id == "start"
    assert all(leg.connector_m == 0 for leg in result.legs)


def test_construction_hold_is_excluded_even_with_a_graph(dataset):
    park, cafe = dataset.pois[:2]
    park = park.model_copy(update={"poi_id": "osm_way_1467797207", "name": "NU Park"})
    result = build_itinerary(request(), Dataset((park, cafe), (), dataset.manifest), SyntheticNetwork())
    assert result.status == "no_match" and not result.stops


def test_poi_accessibility_does_not_imply_an_accessible_route(dataset):
    accessible = tuple(p.model_copy(update={"confirmed_features": {"wheelchair": True}}) for p in dataset.pois)
    result = build_itinerary(request(query="Прогулка безбарьерная"), Dataset(accessible, (), dataset.manifest), SyntheticNetwork())
    assert result.status == "no_match" and "переходов" in result.message


def test_attributed_details_enrich_explanation_without_invented_properties(dataset):
    cafe = dataset.pois[1].model_copy(update={"tags": {"cuisine": "cake;coffee_shop", "takeaway": "yes"}})
    enriched = Dataset((dataset.pois[0], cafe), (), dataset.manifest)
    result = build_itinerary(request(), enriched, SyntheticNetwork())
    assert result.status == "ready"
    stop = next(s for s in result.stops if s.category == "cafe")
    assert "десерты" in stop.why and "с собой" in stop.why
    assert all(f.source_url == cafe.source_url and f.kind == "osm_tag" for f in stop.evidence)
    assert all(f.text in stop.why for f in stop.evidence[:2])


@pytest.mark.parametrize("query", ["Тихая прогулка с розетками", "Прогулка открыто сейчас", "ночная прогулка", "Прогулка перед вылетом", "Прогулка бесплатно", "Хочу интерактивный музей"])
def test_unconfirmed_conditions_are_never_relaxed(dataset, query):
    result = build_itinerary(request(query=query), dataset, SyntheticNetwork())
    assert result.status == "no_match" and not result.stops


def test_same_named_places_do_not_masquerade_as_different_stops(dataset):
    park = dataset.pois[0]
    duplicate = park.model_copy(update={"poi_id": "osm_node_999", "lat": park.lat + .002})
    only_duplicate = Dataset((park, duplicate), (), dataset.manifest)
    result = build_itinerary(request(include_coffee=False), only_duplicate, SyntheticNetwork())
    assert result.status == "no_match"


def test_nearly_identical_centres_do_not_become_two_stops(dataset):
    park, cafe = dataset.pois[:2]
    cafe = cafe.model_copy(update={"lat": park.lat, "lon": park.lon + .0001})
    only_neighbours = Dataset((park, cafe), (), dataset.manifest)
    result = build_itinerary(request(), only_neighbours, SyntheticNetwork())
    assert result.status == "no_match"


@pytest.mark.parametrize("change", [{"available_minutes": 14}, {"available_minutes": 181},
                                    {"available_minutes": 60.0}, {"available_minutes": True},
                                    {"include_coffee": "false"}, {"query": "   "},
                                    {"query": "x" * 1001}, {"lat": float("nan")}, {"extra": 1}])
def test_request_validation(change):
    with pytest.raises(ValidationError):
        ItineraryRequest.model_validate({"lat": START[0], "lon": START[1], "available_minutes": 60} | change)
