"""Read-only place cards from the same validated snapshot as recommendations."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.facts import excluded_from_routes, facts_for, warnings_for
from app.generation import activities_for
from app.models import Evidence, POI
from app.retrieval import Candidate, VISIT_MINUTES


class PlaceCard(POI):
    evidence: list[Evidence]
    warnings: list[str]
    fact_source: Literal["OpenStreetMap", "OpenStreetMap + official sources"]
    activity_source: Literal["suggested_idea"] = "suggested_idea"
    recommendable: bool


class CatalogResponse(BaseModel):
    pois: list[PlaceCard]
    snapshot_id: str


class PlaceInfoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    poi_id: str = Field(pattern=r"^osm_(node|way|relation)_[1-9][0-9]*$", max_length=100)
    locale: Literal["ru", "kz", "en"] = "ru"


class PlaceInfoResponse(BaseModel):
    poi_id: str
    mode: Literal["sourced"] = "sourced"
    summary: str
    tip: str
    source_url: str
    evidence: list[Evidence]
    warnings: list[str]
    fact_source: Literal["OpenStreetMap", "OpenStreetMap + official sources"]
    activity_source: Literal["suggested_idea"] = "suggested_idea"
    recommendable: bool


def place_card(poi: POI) -> PlaceCard:
    facts = facts_for(poi)
    warnings = warnings_for(poi)
    warnings.append(
        "Расписание указано в OSM; актуальность и доступность сейчас не подтверждены."
        if poi.opening_hours else "Часы работы не подтверждены."
    )
    if poi.coordinate_kind != "point":
        warnings.append("Координаты обозначают центр объекта, не проверенный вход.")
    return PlaceCard(
        **poi.model_dump(exclude={"description"}),
        description=" ".join(f["text"] for f in facts[:2]) or poi.description,
        evidence=facts,
        warnings=warnings,
        fact_source="OpenStreetMap + official sources"
        if any(f["kind"] == "official" for f in facts) else "OpenStreetMap",
        recommendable=poi.category in VISIT_MINUTES and not excluded_from_routes(poi),
    )


def place_info(poi: POI) -> PlaceInfoResponse:
    card = place_card(poi)
    minutes = VISIT_MINUTES.get(poi.category, 15)
    candidate = Candidate(poi, 0, 0, minutes, minutes, 0)
    tip = (
        next(iter(activities_for(candidate).values())) if card.recommendable
        else "Эта точка показана для ориентира. Она не включается в рекомендации и мини-маршруты."
    )
    return PlaceInfoResponse(
        poi_id=poi.poi_id,
        summary=card.description,
        tip=tip,
        source_url=poi.source_url,
        evidence=card.evidence,
        warnings=card.warnings,
        fact_source=card.fact_source,
        recommendable=card.recommendable,
    )
