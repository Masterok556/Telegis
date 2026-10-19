"""A bounded, local-only search for an honest walk with a return to its start.

POIs and walking edges come from saved OSM snapshots. The graph must connect
every leg: this module never replaces a missing path with a straight line.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations
from math import ceil
import re
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.data_store import Dataset
from app.facts import excluded_from_routes, facts_for, warnings_for
from app.generation import activities_for
from app.geo import distance_m
from app.models import Evidence, POI
from app.retrieval import (
    Candidate, CATEGORY_PATTERNS, FEATURE_LABELS, LABELS, VISIT_MINUTES, category_constraints,
    explicit_limits, lexical_scores, required_features,
)

if TYPE_CHECKING:
    from app.walking import WalkingLeg, WalkingNetwork


class ItineraryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    available_minutes: int = Field(ge=15, le=180, strict=True)
    query: str = Field(default="Хочу погулять", min_length=1, max_length=1000)
    include_coffee: bool = Field(default=True, strict=True)


class ItineraryContext(BaseModel):
    lat: float
    lon: float
    available_minutes: int
    effective_minutes: int
    include_coffee: bool
    max_distance_m: float
    max_distance_kind: Literal["straight_line_from_start"] = "straight_line_from_start"
    required_features: list[str]
    excluded_categories: list[str]
    return_to_start: Literal[True] = True


class ItineraryStop(BaseModel):
    order: int = Field(ge=1, le=3)
    poi_id: str
    name: str
    lat: float
    lon: float
    category: str
    description: str
    why: str
    activity: str
    visit_minutes_estimate: int = Field(ge=1)
    arrival_minutes_estimate: int = Field(ge=0)
    departure_minutes_estimate: int = Field(ge=0)
    opening_hours: str | None
    source_url: str
    collected_at: str
    evidence: list[Evidence] = Field(default_factory=list)
    fact_source: Literal["OpenStreetMap", "OpenStreetMap + official sources"] = "OpenStreetMap"
    activity_source: Literal["suggested_idea"] = "suggested_idea"
    warnings: list[str]


class ItineraryLeg(BaseModel):
    from_id: str
    to_id: str
    from_name: str
    to_name: str
    distance_m: int = Field(ge=0)
    connector_m: int = Field(ge=0)
    walk_minutes_estimate: int = Field(ge=1)
    coordinates: list[list[float]]
    route_kind: Literal["osm_walking_graph_with_approximate_connectors"] = "osm_walking_graph_with_approximate_connectors"


class ItineraryResponse(BaseModel):
    status: Literal["ready", "no_match", "network_unavailable"]
    mode: Literal["local_graph"] = "local_graph"
    message: str
    why: str = ""
    used_context: ItineraryContext
    stops: list[ItineraryStop] = Field(default_factory=list, max_length=3)
    legs: list[ItineraryLeg] = Field(default_factory=list, max_length=4)
    route_coordinates: list[list[float]] = Field(default_factory=list)
    distance_m: int = Field(default=0, ge=0)
    walking_minutes_estimate: int = Field(default=0, ge=0)
    visit_minutes_estimate: int = Field(default=0, ge=0)
    reserve_minutes: int = Field(ge=5)
    total_minutes_estimate: int = Field(default=0, ge=0)
    remaining_minutes: int = Field(default=0, ge=0)
    suggested_minimum_minutes: int | None = Field(default=None, ge=15, le=180)
    network_snapshot_id: str | None = None
    network_collected_at: str | None = None
    warnings: list[str] = Field(default_factory=list)
    privacy: str = "Маршрут рассчитан локально; координаты и текст запроса не сохраняются и не отправляются модели или внешнему маршрутизатору."
    attribution: str = "© OpenStreetMap contributors"
    license: str = "ODbL 1.0"
    license_url: str = "https://opendatacommons.org/licenses/odbl/1-0/"


@dataclass(frozen=True)
class _Plan:
    stops: tuple[POI, ...]
    legs: tuple[WalkingLeg, ...]
    walking: int
    visiting: int
    score: float


def _reserve(minutes: int) -> int:
    return max(5, ceil(minutes * 0.1))


def _walk_minutes(leg: WalkingLeg) -> int:
    return max(1, ceil(leg.distance_m / 70))


def _minimum_budget(plan: _Plan) -> int | None:
    base = plan.walking + plan.visiting
    return next((m for m in range(15, 181) if base + _reserve(m) <= m), None)


def _unsupported(q: str, payload: ItineraryRequest, dataset: Dataset) -> str:
    coverage = dataset.manifest["coverage"]
    if distance_m(payload.lat, payload.lon, coverage["lat"], coverage["lon"]) > coverage["radius_m"]:
        return "Пока доступны только маршруты в районе EXPO / Mega Silk Way. Выберите стартовую точку в зоне покрытия."
    if re.search(r"\b(?:открыт\w*\s+сейчас|сейчас\s+открыт\w*|ноч\w*|круглосуточ\w*|open\s+now|вылет\w*|аэропорт\w*)\b", q):
        return "Маршрут не подтверждает доступность в реальном времени, ночной доступ и время поездки в аэропорт. Уберите это условие для обычной прогулки."
    if re.search(r"\b(?:интерактив\w*|бесплат\w*|деш[её]в\w*|бюджетн\w*|бюджет\s+(?:до\s+)?\d+(?!\d)(?!\s*(?:минут\w*|мин\b|час\w*|ч\b))|\d+\s*(?:₸|тенге|тг\b)|под\s+крышей|в\s+помещении)", q):
        return "В данных недостаточно сведений для подтверждения дополнительного условия. Оно не будет молча исключено из маршрута."
    return ""


def _candidate_pool(payload: ItineraryRequest, dataset: Dataset, radius: float,
                    features: tuple[str, ...]) -> tuple[list[POI], str, dict[str, float]]:
    q = payload.query.lower()
    interests, excluded = category_constraints(q)
    if payload.include_coffee and "cafe" in excluded:
        return [], "Запрошена кофейная остановка, но текст исключает кафе. Отключите include_coffee или измените запрос.", {}
    if not payload.include_coffee and "cafe" in interests:
        return [], "Текст просит кофе, но include_coffee отключён. Согласуйте запрос и этот переключатель.", {}
    walk_interests = interests - {"cafe"}
    # Walking is an activity rather than a POI category, so category_constraints
    # does not report it. Preserve the common "walk and coffee" request while
    # continuing to reject requests that really only ask for coffee.
    walk_terms = r"(?:прогул\w*|погуля\w*|пройтись|walk\w*|stroll\w*)"
    positive_walk_text = re.sub(r"\b(?:без|не(?:\s+хочу)?|no|without)\s+(?:a\s+)?" + walk_terms + r"\b", "", q)
    explicit_walk = bool(re.search(r"\b" + walk_terms + r"\b", positive_walk_text))
    if interests == {"cafe"} and not explicit_walk:
        return [], "Для мини-маршрута нужны прогулочные остановки. Для одного кофе используйте обычные рекомендации либо добавьте интерес к прогулке или парку.", {}
    if payload.include_coffee and walk_interests and re.search(r"\b(?:только|only)\b", q) and "cafe" not in interests:
        return [], "Текст ограничивает маршрут только выбранными прогулочными местами, а include_coffee добавляет кафе. Отключите кофейную остановку или уточните запрос.", {}
    allowed = set(VISIT_MINUTES) - {"cafe"}
    if walk_interests:
        allowed &= walk_interests
    elif re.search(r"\b(?:реб[её]н\w*|с\s+детьми|children|child)\b", q):
        allowed &= {"park", "garden", "playground"}
    if payload.include_coffee:
        allowed.add("cafe")
    allowed -= excluded
    eligible = [p for p in dataset.pois if p.category in allowed and not excluded_from_routes(p)
                and all(p.confirmed_features.get(f) is True for f in features)
                and distance_m(payload.lat, payload.lon, p.lat, p.lon) <= radius]
    scores = lexical_scores(payload.query, eligible)
    scale = max(scores.values(), default=0) or 1
    scores = {p.poi_id: 0.65 * scores[p.poi_id] / scale
              + 0.35 * (1 - distance_m(payload.lat, payload.lon, p.lat, p.lon) / 2500)
              for p in eligible}
    eligible.sort(key=lambda p: (-scores[p.poi_id], p.poi_id))
    walks = [p for p in eligible if p.category != "cafe"]
    cafes = [p for p in eligible if p.category == "cafe"]
    if not walks or (payload.include_coffee and not cafes):
        detail = " Требуемые свойства проверяются для каждой остановки: " + ", ".join(FEATURE_LABELS[f] for f in features) + "." if features else ""
        return [], "Не хватает подтверждённых мест для прогулки" + (" с кофейной остановкой." if payload.include_coffee else ".") + detail, scores
    return (walks[:8] + cafes[:4] if payload.include_coffee else walks[:12]), "", scores


def _distinct(stops: tuple[POI, ...]) -> bool:
    for first, second in permutations(stops, 2):
        if first.name.casefold().strip() == second.name.casefold().strip():
            return False
        if distance_m(first.lat, first.lon, second.lat, second.lon) < 50:
            return False
    return True


def _joint_interests(query: str) -> list[set[str]]:
    """Honor an explicit 'park AND museum'; 'park OR museum' stays a choice."""
    if not re.search(r"\b(?:и|and)\b", query) or re.search(r"\b(?:или|or)\b", query):
        return []
    interests, _ = category_constraints(query)
    groups = []
    for pattern, categories in CATEGORY_PATTERNS:
        group = (categories & interests) - {"cafe"}
        if group and re.search(r"\b(?:" + pattern + r")\b", query) and group not in groups:
            groups.append(group)
    return groups


def _activity(poi: POI, minutes: int) -> str:
    # Reuse grounded, place-specific ideas without asking the model to invent a
    # route. Choose variants that do not instruct an early return mid-itinerary.
    candidate = Candidate(poi=poi, distance=0, walk_minutes=0, visit_minutes=minutes,
                          total_minutes=minutes, score=0)
    options = activities_for(candidate)
    activity = options.get("photo_walk") or options.get("look_and_photo") or next(iter(options.values()))
    return activity + " Затем переходите к следующему этапу маршрута."


def build_itinerary(payload: ItineraryRequest, dataset: Dataset,
                    network: WalkingNetwork | None) -> ItineraryResponse:
    q = payload.query.lower()
    effective, radius = explicit_limits(q, payload.available_minutes)
    features = required_features(q)
    _, excluded = category_constraints(q)
    reserve = _reserve(effective)
    context = ItineraryContext(lat=payload.lat, lon=payload.lon, available_minutes=payload.available_minutes,
                               effective_minutes=effective, include_coffee=payload.include_coffee,
                               max_distance_m=radius, required_features=list(features),
                               excluded_categories=sorted(excluded))

    def empty(status: str, message: str, suggested: int | None = None) -> ItineraryResponse:
        return ItineraryResponse(status=status, message=message, used_context=context,
                                 reserve_minutes=reserve, suggested_minimum_minutes=suggested)

    blocked = _unsupported(q, payload, dataset)
    if blocked:
        return empty("no_match", blocked)
    if "wheelchair" in features:
        return empty("no_match", "Безбарьерность всех переходов и входов не подтверждена. Даже отметка доступности отдельного места не подтверждает доступность всего маршрута.")
    pool, rejection, relevance = _candidate_pool(payload, dataset, radius, features)
    if rejection:
        return empty("no_match", rejection)
    if network is None:
        return empty("network_unavailable", "Пешеходная сеть недоступна. Маршрут не построен: прямые линии не заменяют реальные дорожки.")

    points = [(payload.lat, payload.lon)] + [(p.lat, p.lon) for p in pool]

    @lru_cache(maxsize=156)
    def leg(a: int, b: int) -> WalkingLeg | None:
        return network.route(points[a], points[b])

    best: _Plan | None = None
    shortest_budget: int | None = None
    connected_plans = 0
    joint_interests = _joint_interests(q)
    for count in (2, 3):
        for indexes in permutations(range(1, len(points)), count):
            stops = tuple(pool[i - 1] for i in indexes)
            if sum(p.category == "cafe" for p in stops) != int(payload.include_coffee) or not _distinct(stops):
                continue
            selected_categories = {p.category for p in stops}
            if not all(selected_categories & group for group in joint_interests):
                continue
            visits = sum(VISIT_MINUTES[p.category] for p in stops)
            if visits + 5 > 180:
                continue
            sequence = (0, *indexes, 0)
            legs = tuple(leg(a, b) for a, b in zip(sequence, sequence[1:]))
            if any(item is None for item in legs):
                continue
            connected_plans += 1
            walking = sum(_walk_minutes(item) for item in legs)
            diversity = len({p.category for p in stops})
            score = 3 * diversity + 2 * count + sum(relevance[p.poi_id] for p in stops) - walking / 20
            plan = _Plan(stops, legs, walking, visits, score)
            minimum = _minimum_budget(plan)
            if minimum is not None:
                shortest_budget = minimum if shortest_budget is None else min(shortest_budget, minimum)
            if walking + visits + reserve > effective:
                continue
            if best is None or (plan.score, -plan.walking, tuple(p.poi_id for p in plan.stops)) > (
                    best.score, -best.walking, tuple(p.poi_id for p in best.stops)):
                best = plan
    if best is None:
        if not connected_plans:
            return empty("no_match", "В выбранных ограничениях не найден связный пешеходный круг минимум через два разных места. Возможно, в OSM не хватает соединяющих дорожек или проверяемых подходов; маршрут не выдуман.")
        message = "Не удалось уместить две разные остановки, дорогу обратно и запас времени. Длительность посещений не сокращается ради результата."
        if shortest_budget is not None and shortest_budget > effective:
            message += f" Для найденного маршрута нужно ориентировочно от {shortest_budget} мин; увеличьте и поле времени, и ограничение в тексте, если оно есть."
        return empty("no_match", message, shortest_budget if shortest_budget and shortest_budget > effective else None)

    ids = ["start", *(p.poi_id for p in best.stops), "start"]
    names = ["Стартовая точка", *(p.name for p in best.stops), "Возвращение к старту"]
    result_legs = [ItineraryLeg(from_id=ids[i], to_id=ids[i + 1], from_name=names[i], to_name=names[i + 1],
                               distance_m=item.distance_m, connector_m=item.connector_m,
                               walk_minutes_estimate=_walk_minutes(item), coordinates=item.coordinates)
                   for i, item in enumerate(best.legs)]
    stops = []
    elapsed = 0
    for i, poi in enumerate(best.stops):
        elapsed += result_legs[i].walk_minutes_estimate
        minutes = VISIT_MINUTES[poi.category]
        warnings = ["Доступность сейчас не подтверждена; время посещения — оценка по категории."]
        warnings.append("Часы работы взяты из OSM и могут быть неактуальны." if poi.opening_hours else "Часы работы неизвестны.")
        if poi.coordinate_kind != "point":
            warnings.append("Точка обозначает центр объекта, а не проверенный вход.")
        warnings.extend(warnings_for(poi))
        facts = facts_for(poi)
        why = " ".join(f["text"] for f in facts[:2])
        if not why:
            why = f"По данным OpenStreetMap это {LABELS.get(poi.category, poi.category).split(',')[0]}. Подробные особенности места в источниках не указаны."
        why += f" На эту остановку отведено {minutes} мин в пределах общего бюджета с возвращением."
        if features:
            why += " В источнике отмечены: " + ", ".join(FEATURE_LABELS[f] for f in features) + "."
        stops.append(ItineraryStop(order=i + 1, poi_id=poi.poi_id, name=poi.name, lat=poi.lat, lon=poi.lon,
                                   category=poi.category, description=poi.description, why=why,
                                   activity=_activity(poi, minutes), visit_minutes_estimate=minutes,
                                   arrival_minutes_estimate=elapsed, departure_minutes_estimate=elapsed + minutes,
                                   opening_hours=poi.opening_hours, source_url=poi.source_url,
                                   collected_at=poi.collected_at, evidence=facts, warnings=warnings,
                                   fact_source="OpenStreetMap + official sources" if any(f["kind"] == "official" for f in facts) else "OpenStreetMap"))
        elapsed += minutes
    coordinates = []
    for item in result_legs:
        coordinates.extend(item.coordinates[1:] if coordinates and item.coordinates and coordinates[-1] == item.coordinates[0] else item.coordinates)
    total = best.walking + best.visiting + reserve
    categories = list(dict.fromkeys(LABELS.get(p.category, p.category).split(',')[0] for p in best.stops))
    why = (f"{' → '.join(categories)}: {len(best.stops)} разных места, {best.walking} мин на все переходы "
           f"включая возвращение, {best.visiting} мин на остановки и {reserve} мин запаса. "
           f"Итого примерно {total} из {effective} мин.")
    warnings = ["Время приблизительное: скорость 70 м/мин, длительность посещений по категории; запас не гарантирует возвращение к точному сроку.",
                "Дорожки взяты из OSM; временные перекрытия, погода, состояние покрытия и доступность входов не проверены.",
                "Маршрут и идеи занятий рассчитаны кодом; сведения о местах взяты из OSM и указанных официальных источников."]
    if any(item.connector_m for item in result_legs):
        warnings.append("Короткие соединения координат с сетью приблизительны и могут пересекать препятствия; проверяйте подходы на месте. Их длина включена во время.")
    metadata = getattr(network, "metadata", {})
    return ItineraryResponse(status="ready", message="Круговой мини-маршрут с возвращением и запасом времени рассчитан по сохранённой пешеходной сети OSM.",
                             why=why, used_context=context, stops=stops, legs=result_legs, route_coordinates=coordinates,
                             distance_m=sum(item.distance_m for item in result_legs), walking_minutes_estimate=best.walking,
                             visit_minutes_estimate=best.visiting, reserve_minutes=reserve,
                             total_minutes_estimate=total, remaining_minutes=effective - total, warnings=warnings,
                             network_snapshot_id=metadata.get("snapshot_id"), network_collected_at=metadata.get("collected_at"))
