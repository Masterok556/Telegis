"""One-way paths to canonical POIs; missing graph paths are honest empty results."""
from math import ceil
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.climate import ClimateContext, climate_allows
from app.data_store import Dataset
from app.facts import excluded_from_routes, warnings_for
from app.geo import distance_m
from app.walking import WalkingNetwork


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    poi_id: str = Field(pattern=r"^osm_(node|way|relation)_[1-9][0-9]*$", max_length=100)
    locale: Literal["ru", "kz", "en"] = "ru"
    climate_shield: bool = Field(default=False, strict=True)


class RouteContext(BaseModel):
    lat: float
    lon: float
    poi_id: str
    locale: Literal["ru", "kz", "en"]
    climate_shield: bool
    climate: ClimateContext
    return_to_start: Literal[False] = False


class RouteResponse(BaseModel):
    status: Literal["ready", "no_match", "network_unavailable"]
    used_context: RouteContext
    coordinates: list[list[float]] = Field(default_factory=list)
    distance_m: int = Field(default=0, ge=0)
    walk_minutes_estimate: int = Field(default=0, ge=0)
    connector_m: int = Field(default=0, ge=0)
    route_kind: Literal["osm_walking_graph_with_approximate_connectors"] = "osm_walking_graph_with_approximate_connectors"
    warnings: list[str] = Field(default_factory=list)
    message: str
    network_snapshot_id: str | None = None
    attribution: str = "© OpenStreetMap contributors"


def build_route(payload: RouteRequest, dataset: Dataset, network: WalkingNetwork | None,
                climate: ClimateContext) -> RouteResponse:
    context = RouteContext(**payload.model_dump(), climate=climate)

    def empty(message: str, status: str = "no_match") -> RouteResponse:
        return RouteResponse(status=status, message=message, used_context=context)

    if climate.policy == "paused":
        return empty(climate.message)
    coverage = dataset.manifest["coverage"]
    if distance_m(payload.lat, payload.lon, coverage["lat"], coverage["lon"]) > coverage["radius_m"]:
        return empty("Старт вне зоны покрытия EXPO / Mega Silk Way.")
    poi = next((p for p in dataset.pois if p.poi_id == payload.poi_id), None)
    if poi is None:
        return empty("Точка отсутствует в проверенном датасете.")
    if excluded_from_routes(poi):
        return empty("Доступность этой точки не подтверждена; маршрут к ней не предлагается.")
    if not climate_allows(poi, climate):
        return empty("Для этой точки нет явного подтверждения помещения. Климатический режим не допускает её в маршрут.")
    if network is None:
        return empty("Пешеходная сеть недоступна. Маршрут не построен: прямые линии не заменяют реальные дорожки.", "network_unavailable")
    leg = network.route((payload.lat, payload.lon), (poi.lat, poi.lon))
    if leg is None:
        return empty("Связный путь к этой точке в сети OSM не найден; линия маршрута не выдумана.")
    warnings = [
        "Это путь в одну сторону; посещение и возвращение не включены во время.",
        "Время рассчитано по сети OSM при скорости 70 м/мин; перекрытия, покрытие и доступность входа не подтверждены.",
        "Часы работы и доступность сейчас не подтверждены.",
        *warnings_for(poi),
    ]
    if leg.connector_m:
        warnings.append("Подходы от координат к сети приблизительны и могут пересекать препятствия; их длина включена во время.")
    if poi.coordinate_kind != "point":
        warnings.append("Координаты обозначают центр объекта, не проверенный вход.")
    if climate.requested:
        warnings.append(climate.message)
    return RouteResponse(
        status="ready", used_context=context, coordinates=leg.coordinates,
        distance_m=leg.distance_m, walk_minutes_estimate=max(1, ceil(leg.distance_m / 70)),
        connector_m=leg.connector_m, warnings=warnings,
        message="Путь в одну сторону рассчитан по сохранённой пешеходной сети OSM.",
        network_snapshot_id=network.metadata.get("snapshot_id"),
    )
