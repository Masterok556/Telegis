"""Deterministic geographic/constraint filtering and lexical BM25 ranking."""
from collections import Counter
from dataclasses import dataclass
from math import ceil, log
import re

from app.data_store import Dataset
from app.geo import distance_m
from app.models import POI, RecommendRequest
from app.facts import facts_for, excluded_from_routes
from app.scenarios import scenario_allows, scenario_flags, scenario_rejection
from app.climate import ClimateContext, climate_context, climate_allows, indoor_evidence

VISIT_MINUTES = {
    "cafe": 15, "park": 20, "garden": 15, "playground": 20,
    "museum": 40, "gallery": 30, "attraction": 15, "viewpoint": 15,
    "artwork": 10, "monument": 10, "memorial": 10,
}
LABELS = {
    "cafe": "кафе, кофе", "park": "парк, прогулка", "garden": "сад, прогулка",
    "playground": "детская площадка", "museum": "музей", "gallery": "галерея",
    "attraction": "достопримечательность", "viewpoint": "смотровая площадка",
    "artwork": "арт-объект", "monument": "памятник", "memorial": "мемориал",
}
ALIASES = {
    "коф": "coffee", "каф": "coffee", "cafe": "coffee", "café": "coffee", "coffee": "coffee",
    "парк": "park", "park": "park", "сад": "garden", "garden": "garden",
    "музе": "museum", "museum": "museum", "галере": "gallery", "gallery": "gallery",
    "прогул": "walk", "погул": "walk", "walk": "walk",
    "памят": "monument", "monument": "monument", "арт": "art", "art": "art",
    "дет": "children", "ребён": "children", "ребен": "children", "child": "children",
    "саябақ": "park", "мұражай": "museum", "серуен": "walk", "бала": "children",
}
FEATURE_PATTERNS = {
    "socket": r"розет\w*|socket\w*|power\s*outlet\w*",
    "wifi": r"wi[ -]?fi|вай[ -]?фай|интернет\w*",
    "quiet": r"тих\w*|тишин\w*|quiet\w*|тыныш\w*",
    "wheelchair": r"инвалид\w*|wheelchair\w*|безбарьер\w*|мүгедек\w*",
}
FEATURE_LABELS = {"socket": "розетки", "wifi": "Wi-Fi", "quiet": "тишина", "wheelchair": "доступность для кресла-коляски"}
CATEGORY_PATTERNS = (
    (r"музе\w*|museums?|мұражай\w*", {"museum"}),
    (r"парк(?:а|е|и|ом|ов|ам|ах|у)?|parks?|саябақ\w*", {"park", "garden"}),
    (r"сад(?:а|у|ом|ы|ов|ах)?|gardens?", {"garden"}),
    (r"галере\w*|galler(?:y|ies)", {"gallery"}),
    (r"смотров\w*(?:\s+площад\w*)?|viewpoints?", {"viewpoint"}),
    (r"дет\w*\s+площад\w*|playgrounds?|балалар\s+алаң\w*", {"playground"}),
    (r"кофе|кафе|кофейн\w*|coffee|caf[eé]s?", {"cafe"}),
    (r"памятник\w*|monuments?", {"monument", "memorial"}),
    (r"мемориал\w*|memorials?", {"memorial"}),
    (r"арт[ -]?объект\w*|artworks?", {"artwork"}),
)


@dataclass(frozen=True)
class Candidate:
    poi: POI
    distance: int
    walk_minutes: int
    visit_minutes: int
    total_minutes: int
    score: float
    route_distance_m: int | None = None
    return_route_distance_m: int | None = None
    route_connector_m: int | None = None
    scenarios: tuple[str, ...] = ()
    climate_shielded: bool = False


@dataclass(frozen=True)
class RetrievalResult:
    candidates: tuple[Candidate, ...]
    message: str
    required_features: tuple[str, ...] = ()
    effective_minutes: int | None = None
    max_distance_m: float = 2500.0
    excluded_categories: tuple[str, ...] = ()


def tokens(text: str) -> list[str]:
    result = []
    for token in re.findall(r"[a-zа-яёқғңүұөіәһ]+", text.lower()):
        if len(token) < 3:
            continue
        result.append(next((v for prefix, v in ALIASES.items() if token.startswith(prefix)), token))
    return result


def required_features(query: str) -> tuple[str, ...]:
    # Remove common explicitly waived requirements; other mentions are conservative constraints.
    q = query.lower()
    feature = "(?:" + "|".join(FEATURE_PATTERNS.values()) + ")"
    waive = r"(?:не\s+(?:нуж\w*|обязательн\w*|важн\w*|требу\w*)|not\s+(?:needed|required|necessary)|қажет\s+емес)"
    q = re.sub(r"\b(?:без|" + waive + r")\s+" + feature + r"(?:\s*(?:,|и|или|and|or)\s*" + feature + r")*", "", q)
    q = re.sub(feature + r"(?:\s*(?:,|и|или|and|or)\s*" + feature + r")*\s+" + waive, "", q)
    return tuple(key for key, pattern in FEATURE_PATTERNS.items() if re.search(r"\b(?:" + pattern + r")\b", q))


def category_constraints(query: str) -> tuple[set[str], set[str]]:
    """Recognize simple interests/exclusions without treating nearby landmarks as goals."""
    all_terms = "(?:" + "|".join(pattern for pattern, _ in CATEGORY_PATTERNS) + ")"
    negative = r"(?:без|кроме|исключая|никаких|не(?:\s+(?:хочу|хочется|нужен|нужна|нужно|нужны|надо|интересует|интересуют))?(?:\s+в)?|not|no|except)"
    spans = [match.span() for match in re.finditer(
        r"\b" + negative + r"\s+" + all_terms + r"\b(?:\s*(?:,|и|или|and|or)\s*" + all_terms + r"\b)*", query)]
    interests, excluded = set(), set()
    for pattern, categories in CATEGORY_PATTERNS:
        for match in re.finditer(r"\b(?:" + pattern + r")\b", query):
            before, after = query[:match.start()], query[match.end():]
            if any(start <= match.start() < end for start, end in spans) or re.match(
                r"\s+(?:не\s+(?:нуж\w*|интересу\w*|надо)|қажет\s+емес|керек\s+емес)\b", after
            ):
                excluded.update(categories)
            elif re.search(r"\b(?:у|возле|около|рядом\s+с|near|next\s+to)\s+(?:здания\s+)?$", before) or re.search(
                r"\b(?:я|сейчас|нахожусь|стою)\s+в\s+$", before
            ):
                continue
            else:
                interests.update(categories)
    return interests, excluded


def explicit_limits(query: str, available_minutes: int) -> tuple[int, float]:
    """A few unambiguous numeric limits; never increase the form's time allowance."""
    minutes, radius = available_minutes, 2500.0
    for match in re.finditer(r"\b(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*(minutes?|mins?|hours?|hrs?)\b", query):
        minutes = min(minutes, int(match[2] or match[1]) * (60 if match[3].startswith("h") else 1))
    if re.search(r"[әғқңөұүһі]|серуен|баламен|кофе\s+керек", query):
        for match in re.finditer(r"\b(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*(минут\w*|сағат\w*)\b", query):
            minutes = min(minutes, int(match[2] or match[1]) * (60 if match[3].startswith("сағат") else 1))
    for match in re.finditer(
        r"\b(?:на|за|есть|осталось|всего|меня|максимум|бюджет(?:\s+времени)?|не\s+(?:более|больше)|до|уложиться\s+в)\s+"
        r"(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\s*(минут\w*|мин\b|час\w*|ч\b)", query
    ):
        amount = int(match[2] or match[1])
        minutes = min(minutes, amount * (60 if match[3].startswith("ч") else 1))
    for match in re.finditer(
        r"\b(?:не\s+(?:дальше|далее|более|больше)|максимум|в\s+радиусе|в\s+пределах|до)\s+"
        r"(\d+(?:[.,]\d+)?)\s*(километр\w*|км\b|метр\w*|м\b)", query
    ):
        radius = min(radius, float(match[1].replace(",", ".")) * (1000 if match[2].startswith("к") else 1))
    return minutes, radius


def lexical_scores(query: str, pois: list[POI]) -> dict[str, float]:
    """Small-corpus BM25. Category aliases provide limited RU/EN normalization."""
    documents = [Counter(tokens(" ".join([p.name, p.description, LABELS.get(p.category, p.category),
                                         *p.tags.values(), *(f["text"] for f in facts_for(p))]))) for p in pois]
    if not documents:
        return {}
    average = max(1.0, sum(sum(d.values()) for d in documents) / len(documents))
    terms = set(tokens(query))
    frequency = {t: sum(t in d for d in documents) for t in terms}
    scores = {}
    for poi, doc in zip(pois, documents):
        score = 0.0
        for term in terms:
            tf = doc[term]
            if not tf:
                continue
            idf = log(1 + (len(documents) - frequency[term] + 0.5) / (frequency[term] + 0.5))
            score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * sum(doc.values()) / average))
        if "tourist" in scenario_flags(query):
            score += 2 * int(poi.category in {"museum", "gallery", "attraction", "viewpoint", "monument", "memorial", "artwork"})
            score += 2 * int(any(f["kind"] == "official" for f in facts_for(poi)))
        scores[poi.poi_id] = score
    return scores


def retrieve(request: RecommendRequest, dataset: Dataset, network=None,
             climate: ClimateContext | None = None) -> RetrievalResult:
    q = request.query.lower()
    required = required_features(q)
    category_interests, excluded = category_constraints(q)
    available_minutes, max_distance = explicit_limits(q, request.available_minutes)
    climate = climate or climate_context(request.climate_shield)

    def result(candidates: tuple[Candidate, ...], message: str) -> RetrievalResult:
        return RetrievalResult(candidates, message, required, available_minutes, max_distance, tuple(sorted(excluded)))

    coverage = dataset.manifest["coverage"]
    if climate.policy == "paused":
        return result((), climate.message)
    if distance_m(request.lat, request.lon, coverage["lat"], coverage["lon"]) > coverage["radius_m"]:
        return result((), "Пока доступны только места в районе EXPO / Mega Silk Way. Выберите стартовую точку в зоне покрытия.")
    blocked = scenario_rejection(q)
    if blocked:
        return result((), blocked)
    allowed = {"cafe"} if request.category == "cafe" else set(VISIT_MINUTES) - {"cafe"}
    # Explicit narrower interests must not be silently replaced with unrelated POI.
    if category_interests:
        allowed &= category_interests
        if not allowed:
            return result((), "Текст запроса и выбранная категория расходятся. Переключите «Прогулка» / «Кофе» или уточните запрос.")
    elif request.category == "walk" and "family" in scenario_flags(q):
        # Accompanying a child does not override an explicit museum or cafe interest.
        allowed &= {"park", "garden", "playground"}
    allowed -= excluded
    eligible = [p for p in dataset.pois if p.category in allowed and not excluded_from_routes(p) and scenario_allows(p, q)
                and climate_allows(p, climate, q)
                and all(p.confirmed_features.get(f) is True for f in required)]
    if not eligible:
        detail = " Не подтверждены условия: " + ", ".join(FEATURE_LABELS[f] for f in required) + "." if required else ""
        if climate.policy == "indoor_only":
            detail += " Нужны явные данные о помещении; категория кафе или музей этого не подтверждает."
        return result((), "В этой части датасета нет подходящих мест." + detail)
    scores = lexical_scores(request.query, eligible)
    max_score = max(scores.values(), default=0) or 1
    candidates = []
    for poi in eligible:
        direct_distance = distance_m(request.lat, request.lon, poi.lat, poi.lon)
        if direct_distance > max_distance:
            continue
        meters = round(direct_distance)
        # A transparent heuristic, not a route: detour factor 1.3 / speed 70m/min.
        # Add a fixed entrance/orientation margin. Park/mall centers are not entrances.
        routed = returned = None
        if network is not None:
            routed = network.route((request.lat, request.lon), (poi.lat, poi.lon))
            returned = network.route((poi.lat, poi.lon), (request.lat, request.lon))
            if routed is None or returned is None:
                continue
            # Keep the established 2*walk+visit contract, conservatively using
            # the longer direction when pedestrian one-way rules differ.
            walk = max(1, ceil(max(routed.distance_m, returned.distance_m) / 70)) + 2
        else:
            walk = max(1, ceil(meters * 1.3 / 70)) + 2
        visit = VISIT_MINUTES[poi.category]
        total = 2 * walk + visit
        if total > available_minutes:
            continue
        score = 0.65 * (scores[poi.poi_id] / max_score) + 0.35 * (1 - meters / 2500)
        if "family" in scenario_flags(q) and poi.category == "playground":
            score += 0.4
        is_shielded = bool(indoor_evidence(poi))
        candidates.append(Candidate(poi, meters, walk, visit, total, score,
                                    routed.distance_m if routed else None,
                                    returned.distance_m if returned else None,
                                    routed.connector_m + returned.connector_m if routed else None, scenario_flags(q),
                                    climate_shielded=is_shielded))
    candidates.sort(key=lambda c: (-c.score, c.distance, c.poi.poi_id))
    if not candidates:
        return result((), "Подходящих мест с посещением и возвращением в указанные ограничения времени и расстояния не найдено. Попробуйте увеличить время или радиус." +
                      (" Для части мест может не быть связного пути в сохранённой сети OSM." if network is not None else ""))
    return result(tuple(candidates[:5]), "")
