"""Deterministic geographic/constraint filtering and lexical BM25 ranking."""
from collections import Counter
from dataclasses import dataclass
from math import ceil, log
import re

from app.data_store import Dataset
from app.geo import distance_m
from app.models import POI, RecommendRequest

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
}
FEATURE_PATTERNS = {
    "socket": r"розет\w*|socket\w*|power\s*outlet\w*",
    "wifi": r"wi[ -]?fi|вай[ -]?фай|интернет\w*",
    "quiet": r"тих\w*|тишин\w*|quiet\w*",
    "wheelchair": r"инвалид\w*|wheelchair\w*|безбарьер\w*",
}
FEATURE_LABELS = {"socket": "розетки", "wifi": "Wi-Fi", "quiet": "тишина", "wheelchair": "доступность для кресла-коляски"}


@dataclass(frozen=True)
class Candidate:
    poi: POI
    distance: int
    walk_minutes: int
    visit_minutes: int
    total_minutes: int
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    candidates: tuple[Candidate, ...]
    message: str
    required_features: tuple[str, ...] = ()


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
    q = re.sub(r"(?:без|не\s+нужн\w*|не\s+обязательн\w*)\s+(?:розет\w*|wi[ -]?fi|вай[ -]?фай|тишин\w*)", "", q)
    q = re.sub(r"(?:розет\w*|wi[ -]?fi|вай[ -]?фай|тишин\w*)\s+(?:не\s+нужн\w*|не\s+обязательн\w*)", "", q)
    return tuple(key for key, pattern in FEATURE_PATTERNS.items() if re.search(pattern, q))


def lexical_scores(query: str, pois: list[POI]) -> dict[str, float]:
    """Small-corpus BM25. Category aliases provide limited RU/EN normalization."""
    documents = [Counter(tokens(" ".join([p.name, p.description, LABELS.get(p.category, p.category), *p.tags.values()]))) for p in pois]
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
        scores[poi.poi_id] = score
    return scores


def retrieve(request: RecommendRequest, dataset: Dataset) -> RetrievalResult:
    coverage = dataset.manifest["coverage"]
    if distance_m(request.lat, request.lon, coverage["lat"], coverage["lon"]) > coverage["radius_m"]:
        return RetrievalResult((), "Пока доступны только места в районе EXPO / Mega Silk Way. Выберите стартовую точку в зоне покрытия.")
    q = request.query.lower()
    if re.search(r"открыт\w*\s+сейчас|сейчас\s+открыт|ноч\w*|круглосуточ\w*|open\s+now|вылет|аэропорт", q):
        return RetrievalResult((), "Этот прототип не проверяет доступность в реальном времени и не рассчитывает поездки в аэропорт. Выберите прогулку или кофе без такого условия.")
    if re.search(r"интерактив\w*|бесплат\w*|деш[её]в\w*|бюджет\w*|\d+\s*(?:₸|тенге|тг\b)|под\s+крышей|в\s+помещении", q):
        return RetrievalResult((), "В собранных данных недостаточно сведений, чтобы подтвердить указанное дополнительное условие. Уточните запрос или уберите это условие.")
    required = required_features(q)
    allowed = {"cafe"} if request.category == "cafe" else set(VISIT_MINUTES) - {"cafe"}
    # Explicit narrower interests must not be silently replaced with unrelated POI.
    category_interests: set[str] = set()
    for pattern, categories in [
        (r"музе\w*|museum", {"museum"}), (r"парк\w*|\bpark\b", {"park", "garden"}),
        (r"галере\w*|gallery", {"gallery"}), (r"смотров\w*|viewpoint", {"viewpoint"}),
        (r"дет\w*\s+площад\w*|реб[её]н\w*|с\s+детьми|playground", {"playground"}),
        (r"кофе|кафе|coffee|cafe", {"cafe"}),
    ]:
        if re.search(pattern, q):
            category_interests.update(categories)
    if category_interests:
        allowed &= category_interests
        if not allowed:
            return RetrievalResult((), "Текст запроса и выбранная категория расходятся. Переключите «Прогулка» / «Кофе» или уточните запрос.", required)
    eligible = [p for p in dataset.pois if p.category in allowed and all(p.confirmed_features.get(f) is True for f in required)]
    if not eligible:
        detail = " Не подтверждены условия: " + ", ".join(FEATURE_LABELS[f] for f in required) + "." if required else ""
        return RetrievalResult((), "В этой части датасета нет подходящих мест." + detail, required)
    scores = lexical_scores(request.query, eligible)
    max_score = max(scores.values(), default=0) or 1
    candidates = []
    for poi in eligible:
        meters = round(distance_m(request.lat, request.lon, poi.lat, poi.lon))
        if meters > 2500:
            continue
        # A transparent heuristic, not a route: detour factor 1.3 / speed 70m/min.
        # Add a fixed entrance/orientation margin. Park/mall centers are not entrances.
        walk = max(1, ceil(meters * 1.3 / 70)) + 2
        visit = VISIT_MINUTES[poi.category]
        total = 2 * walk + visit
        if total > request.available_minutes:
            continue
        score = 0.65 * (scores[poi.poi_id] / max_score) + 0.35 * (1 - meters / 2500)
        candidates.append(Candidate(poi, meters, walk, visit, total, score))
    candidates.sort(key=lambda c: (-c.score, c.distance, c.poi.poi_id))
    if not candidates:
        return RetrievalResult((), "Подходящих мест с посещением и возвращением в выбранный бюджет времени не найдено. Попробуйте увеличить время.", required)
    return RetrievalResult(tuple(candidates[:5]), "", required)
