from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.data_store import DataStore, DatasetUnavailable
from app.generation import Generator
from app.models import LocationsResponse, RecommendRequest, RecommendResponse, Recommendation, UsedContext
from app.retrieval import retrieve
from app.facts import facts_for, warnings_for, excluded_from_routes
from app.scenarios import scenario_warnings
from app.itinerary import ItineraryRequest, ItineraryResponse, build_itinerary
from app.walking import WalkingNetwork
from app.catalog import CatalogResponse, PlaceInfoRequest, PlaceInfoResponse, place_card, place_info
from app.climate import climate_context, indoor_evidence
from app.weather import WeatherService, WeatherSnapshot
from app.point_route import RouteRequest, RouteResponse, build_route


def localized(value, locale: str):
    from app.localization import localize_response
    return localize_response(value.model_dump(mode="json") if hasattr(value, "model_dump") else value, locale)


@lru_cache(maxsize=2)
def _load_walking(root: Path, pointer: str) -> WalkingNetwork:
    # Cache immutable public OSM graphs, never requests or exact user positions.
    return WalkingNetwork.load(root)


def walking_network(root: Path) -> WalkingNetwork | None:
    try:
        return _load_walking(root, (root / "current.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError):
        return None


class OptionalStaticFiles(StaticFiles):
    """Works even if the frontend folder is supplied after API startup."""
    async def get_response(self, path, scope):
        if not self.directory or not Path(self.directory).is_dir():
            raise HTTPException(status_code=404, detail="Файлы интерфейса ещё не добавлены")
        return await super().get_response(path, scope)

    async def check_config(self):
        # Missing directory is an expected integration state, not a startup failure.
        return None


def create_app(settings: Settings | None = None, generator: Generator | None = None,
               weather_service: WeatherService | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    store = DataStore(config.data_dir)
    generator = generator or Generator(config)
    weather_service = weather_service or WeatherService()
    api = FastAPI(title="Telegis", version="1.4.0", description="AI-гид по Астане: факты с источниками, проверяемая погода и мини-маршруты с возвращением и запасом времени.")
    api.state.store = store
    api.state.settings = config
    api.state.generator = generator
    api.state.weather = weather_service

    async def request_climate(enabled: bool):
        return climate_context(enabled, await weather_service.get() if enabled else None)
    # No access logs containing IPs/queries, no outbound HTTP logs with provider URLs.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    if config.cors_origins:
        api.add_middleware(CORSMiddleware, allow_origins=list(config.cors_origins),
                           allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @api.middleware("http")
    async def privacy_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # OSM browser tiles require a Referer. Send only the page origin to
        # external resources; API responses still disclose no referrer.
        response.headers["Referrer-Policy"] = (
            "no-referrer" if request.url.path.startswith("/api/")
            else "strict-origin-when-cross-origin"
        )
        return response

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # FastAPI's default error includes rejected input values. Avoid echoing GPS/query.
        errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @api.exception_handler(DatasetUnavailable)
    async def unavailable(request: Request, exc: DatasetUnavailable):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @api.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🧭</text></svg>'
        return Response(content=svg, media_type="image/svg+xml")

    @api.get("/api/health")
    async def health():
        try:
            dataset = store.get()
            return {"status": "ok", "poi_count": len(dataset.pois), "llm_configured": config.llm_configured,
                    "service": "Telegis", "llm_last_status": generator.last_status,
                    "snapshot_id": dataset.manifest["snapshot_id"]}
        except DatasetUnavailable:
            return JSONResponse(status_code=503, content={"status": "missing_data", "poi_count": 0,
                                                         "llm_configured": config.llm_configured})

    @api.get("/api/locations", response_model=LocationsResponse)
    async def locations(locale: Literal["ru", "kz", "en"] = "ru"):
        return localized(LocationsResponse(locations=list(store.get().locations)), locale)

    @api.get("/api/pois", response_model=CatalogResponse)
    def pois(locale: Literal["ru", "kz", "en"] = "ru"):
        dataset = store.get()
        return localized(CatalogResponse(pois=[place_card(p) for p in dataset.pois],
                               snapshot_id=dataset.manifest["snapshot_id"]), locale)

    @api.post("/api/poi_ai_info", response_model=PlaceInfoResponse)
    def poi_info(payload: PlaceInfoRequest):
        # The legacy UI path is retained, but cards use sourced facts, not
        # unbounded model output. Client-supplied names/facts are never accepted.
        poi = next((p for p in store.get().pois if p.poi_id == payload.poi_id), None)
        if poi is None:
            raise HTTPException(status_code=404, detail="Точка отсутствует в проверенном датасете.")
        return localized(place_info(poi), payload.locale)

    @api.get("/api/walking-map.geojson")
    def walking_map():
        network = walking_network(config.walking_dir or config.data_dir / "walking")
        if network is None:
            raise HTTPException(status_code=503, detail="Локальная схема дорожек недоступна.")
        return network.map_geojson()

    @api.get("/api/meta")
    async def meta(locale: Literal["ru", "kz", "en"] = "ru"):
        dataset = store.get()
        manifest = dataset.manifest
        network = walking_network(config.walking_dir or config.data_dir / "walking")
        all_facts = [facts_for(p) for p in dataset.pois]
        body = {key: manifest[key] for key in ("poi_count", "categories", "collected_at", "source_data_timestamp",
                                               "coverage", "attribution", "license", "license_url", "snapshot_id")} | {
            "retrieval": "geographic filters + lexical BM25",
            "llm_configured": config.llm_configured,
            "llm_last_status": generator.last_status,
            "llm_model": config.llm_model if config.llm_configured else None,
            "service": "Telegis",
            "data_quality": {
                "with_opening_hours": sum(bool(p.opening_hours) for p in dataset.pois),
                "with_contacts": sum(bool(p.phone or p.website) for p in dataset.pois),
                "confirmed_features": {feature: sum(p.confirmed_features.get(feature) is True for p in dataset.pois)
                                       for feature in ("wifi", "socket", "quiet", "wheelchair")},
                "ratings_available": False,
                "with_informative_facts": sum(bool(facts) for facts in all_facts),
                "attributed_fact_count": sum(len(facts) for facts in all_facts),
                "official_fact_count": sum(f["kind"] == "official" for facts in all_facts for f in facts),
                "with_explicit_indoor_evidence": sum(bool(indoor_evidence(p)) for p in dataset.pois),
                "excluded_pending_verification": [
                    {"poi_id": p.poi_id, "name": p.name, "warnings": warnings_for(p)}
                    for p in dataset.pois if excluded_from_routes(p)
                ],
            },
            "capabilities": ["grounded_recommendations", "attributed_place_facts", "return_with_time_reserve",
                             "model_weather_with_freshness", "evidence_based_climate_filter", "single_destination_graph_route"],
            "weather": {"provider": "Open-Meteo", "location_kind": "fixed_public_area",
                        "user_coordinates_sent": False, "source_url": "https://open-meteo.com/en/docs",
                        "live_label_means": "fresh_model_estimate_not_station_observation",
                        "demo_affects_recommendations": False},
            "walking_network": {"available": network is not None, **({
                key: network.metadata.get(key) for key in ("snapshot_id", "collected_at", "node_count", "directed_edge_count", "source_data_timestamp", "max_snap_m")
            } if network else {})},
            "time_estimate": "With graph: one-way estimate = max(1, ceil(max(outward_m, return_m)/70)) + 2; otherwise straight_line_m*1.3/70 + margin. Total = 2*one-way + visit. Itinerary sums individual graph legs + visits + reserve.",
            "limitations": ["distance_m — расстояние по прямой. При наличии сети OSM время рассчитывается по путям с приблизительными подходами до 120 м; travel_basis показывает метод.",
                            "Часы и доступность в реальном времени не подтверждаются.",
                            "Точки крупных объектов могут быть центрами территории, а не входами.",
                            "Время посещения — эвристика по категории, не данные объекта.",
                            "Лексический поиск и правила понимают ограниченный набор условий."],
            "privacy": "Нет хранения запросов/GPS и аналитики; модели передаются выбранные POI и нормализованные ограничения, без исходного текста и координат пользователя.",
        }
        return localized(body, locale)

    @api.get("/api/weather", response_model=WeatherSnapshot)
    async def get_weather(demo: bool = False, locale: Literal["ru", "kz", "en"] = "ru"):
        return localized(await weather_service.get(demo=demo), locale)

    @api.post("/api/recommend", response_model=RecommendResponse)
    async def recommend(payload: RecommendRequest):
        dataset = store.get()
        climate = await request_climate(payload.climate_shield)
        result = await run_in_threadpool(retrieve, payload, dataset,
                                        walking_network(config.walking_dir or config.data_dir / "walking"), climate)
        context = UsedContext(**payload.model_dump(exclude={"query"}),
                              effective_minutes=result.effective_minutes, max_distance_m=result.max_distance_m,
                              required_features=list(result.required_features), excluded_categories=list(result.excluded_categories),
                              climate=climate)
        if not result.candidates:
            return localized(RecommendResponse(mode="fallback", used_context=context, recommendations=[], message=result.message), payload.locale)
        effective = payload.model_copy(update={"available_minutes": result.effective_minutes or payload.available_minutes})
        generated = await generator.generate(effective, result.candidates, result.required_features)
        recommendations = []
        for choice in generated.choices:
            candidate, poi = choice.candidate, choice.candidate.poi
            facts = facts_for(poi)
            warnings = (["Расстояние distance_m — по прямой; время рассчитано по сети OSM с приблизительными подходами и запасом на вход. Обходы, временные ограничения и доступность входов не проверены."]
                        if candidate.route_distance_m is not None else ["Расстояние по прямой; время приблизительное, пешеходный маршрут не рассчитан."])
            if poi.opening_hours:
                warnings.append("Расписание взято из OpenStreetMap; актуальность и доступность сейчас не подтверждены.")
            else:
                warnings.append("Часы работы не подтверждены.")
            if poi.coordinate_kind != "point":
                warnings.append("Координаты обозначают центр объекта, не проверенный вход.")
            collected = datetime.fromisoformat(poi.collected_at.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - collected).total_seconds() > 7 * 86400:
                warnings.append("Датасет собран более недели назад; сведения могли измениться.")
            warnings.extend(warnings_for(poi))
            warnings.extend(scenario_warnings(payload.query))
            if climate.policy == "indoor_only":
                warnings.append(climate.message)
            recommendations.append(Recommendation(
                poi_id=poi.poi_id, name=poi.name, lat=poi.lat, lon=poi.lon, category=poi.category,
                distance_m=candidate.distance, walk_minutes_estimate=candidate.walk_minutes,
                visit_minutes_estimate=candidate.visit_minutes, total_minutes_estimate=candidate.total_minutes,
                why=choice.why, activity=choice.activity, opening_hours=poi.opening_hours,
                source_url=poi.source_url, collected_at=poi.collected_at, warnings=warnings,
                description=" ".join(f["text"] for f in facts[:2]) or poi.description,
                phone=poi.phone, website=poi.website,
                evidence=facts[:6], time_margin_minutes=max(0, effective.available_minutes - candidate.total_minutes),
                fact_source="OpenStreetMap + official sources" if any(f["kind"] == "official" for f in facts) else "OpenStreetMap",
                travel_basis="osm_walking_graph" if candidate.route_distance_m is not None else "straight_line_estimate",
                route_distance_m=candidate.route_distance_m, return_route_distance_m=candidate.return_route_distance_m,
                route_connector_m=candidate.route_connector_m,
                climate_shielded=candidate.climate_shielded,
                indoor_evidence=indoor_evidence(poi),
            ))
        return localized(RecommendResponse(mode=generated.mode, used_context=context, recommendations=recommendations, message=generated.message), payload.locale)

    @api.post("/api/itinerary", response_model=ItineraryResponse)
    async def itinerary(payload: ItineraryRequest):
        climate = await request_climate(payload.climate_shield)
        result = await run_in_threadpool(build_itinerary, payload, store.get(),
                                        walking_network(config.walking_dir or config.data_dir / "walking"), climate)
        return localized(result, payload.locale)

    @api.post("/api/route", response_model=RouteResponse)
    async def route(payload: RouteRequest):
        climate = await request_climate(payload.climate_shield)
        result = await run_in_threadpool(build_route, payload, store.get(),
                                        walking_network(config.walking_dir or config.data_dir / "walking"), climate)
        return localized(result, payload.locale)

    @api.get("/", include_in_schema=False)
    async def index():
        target = config.static_dir / "index.html"
        if target.is_file():
            return FileResponse(target)
        return JSONResponse({"service": "Telegis", "message": "Бэкенд Telegis готов. Добавьте static/index.html от участника 2.", "api_docs": "/docs"})

    api.mount("/static", OptionalStaticFiles(directory=str(config.static_dir), check_dir=False), name="static")
    api.mount("/presentation", OptionalStaticFiles(directory=str(config.static_dir.parent / "presentation"),
                                                   check_dir=False), name="presentation")
    return api


app = create_app()
