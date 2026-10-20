"""Shared climate decisions. A building is never inferred from its name/category."""
from __future__ import annotations

import re
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from app.weather import WeatherSnapshot

if TYPE_CHECKING:
    from app.models import POI


class ClimateContext(BaseModel):
    requested: bool = False
    applied: bool = False
    policy: Literal["off", "normal", "indoor_only", "paused"] = "off"
    reason_codes: list[str] = Field(default_factory=list)
    message: str = "Климатический режим выключен; погода не влияет на выбор."
    weather: WeatherSnapshot | None = None
    outdoor_travel_unverified: Literal[True] = True


def climate_context(requested: bool, weather: WeatherSnapshot | None = None) -> ClimateContext:
    if not requested:
        return ClimateContext()
    # Synthetic weather can be inspected separately, never used as live evidence.
    if weather is None or weather.status != "live" or weather.current is None:
        return ClimateContext(
            requested=True, policy="paused", weather=weather,
            reason_codes=["weather_not_current"],
            message="Климатический режим приостановлен: актуальная погода не подтверждена. "
                    "Повторите запрос позже или явно выключите этот режим для обычного поиска.",
        )
    mode = weather.policy.mode
    if mode == "unknown":
        return ClimateContext(
            requested=True, policy="paused", weather=weather,
            reason_codes=weather.policy.reasons,
            message="Климатическая адаптация недоступна: недостаточно погодных данных.",
        )
    return ClimateContext(
        requested=True, applied=True, weather=weather,
        policy={"normal": "normal", "prefer_indoor": "indoor_only",
                "avoid_outdoor": "paused"}[mode],
        reason_codes=weather.policy.reasons, message=weather.policy.message,
    )


def indoor_evidence(poi: POI) -> list[dict]:
    """Positive explicit OSM tags only; conflicting outdoor evidence wins."""
    if poi.tags.get("indoor") == "no":
        return []
    rows = []
    for key, text in (
        ("indoor", "В OSM явно отмечено расположение внутри помещения."),
        ("indoor_seating", "В OSM явно отмечены места для сидения внутри."),
    ):
        if poi.tags.get(key) == "yes":
            rows.append({"id": "osm_" + key, "text": text, "source_url": poi.source_url,
                         "collected_at": poi.collected_at, "kind": "osm_tag",
                         "confidence": "source_reported"})
    return rows


def requires_indoor(query: str) -> bool:
    # Explicit destination preference is independent of weather. Do not silently
    # activate weather adaptation from a casual mention of cold or wind.
    q = query.lower()
    term = r"(?:indoor\w*|в\s+помещени\w*|внутри\s+здани\w*|под\s+крышей|жабық\s+орын)"
    q = re.sub(r"\b(?:не(?:\s+(?:нужно|хочу))?|not|no)\s+" + term + r"\b", "", q)
    q = re.sub(term + r"\s+(?:(?:қажет|керек)\s+)?емес\b", "", q)
    return bool(re.search(r"\b(?:indoor\w*|в\s+помещени\w*|внутри\s+здани\w*|под\s+крышей|жабық\s+орын)\b", q))


def climate_allows(poi: POI, context: ClimateContext, query: str = "") -> bool:
    if context.policy == "paused":
        return False
    return bool(indoor_evidence(poi)) if context.policy == "indoor_only" or requires_indoor(query) else True
