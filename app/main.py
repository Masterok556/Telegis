from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.data_store import DataStore, DatasetUnavailable
from app.generation import Generator
from app.models import LocationsResponse, RecommendRequest, RecommendResponse, Recommendation, UsedContext
from app.retrieval import retrieve


class OptionalStaticFiles(StaticFiles):
    """Works even if the frontend folder is supplied after API startup."""
    async def get_response(self, path, scope):
        if not self.directory or not Path(self.directory).is_dir():
            raise HTTPException(status_code=404, detail="Файлы интерфейса ещё не добавлены")
        return await super().get_response(path, scope)

    async def check_config(self):
        # Missing directory is an expected integration state, not a startup failure.
        return None


def create_app(settings: Settings | None = None, generator: Generator | None = None) -> FastAPI:
    config = settings or Settings.from_env()
    store = DataStore(config.data_dir)
    generator = generator or Generator(config)
    api = FastAPI(title="Telegis", version="1.1.0", description="AI-гид по Астане: реальные места, учёт времени и проверяемые рекомендации.")
    api.state.store = store
    api.state.settings = config
    api.state.generator = generator
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
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # FastAPI's default error includes rejected input values. Avoid echoing GPS/query.
        errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @api.exception_handler(DatasetUnavailable)
    async def unavailable(request: Request, exc: DatasetUnavailable):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

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
    async def locations():
        return LocationsResponse(locations=list(store.get().locations))

    @api.get("/api/meta")
    async def meta():
        dataset = store.get()
        manifest = dataset.manifest
        return {key: manifest[key] for key in ("poi_count", "categories", "collected_at", "source_data_timestamp",
                                               "coverage", "attribution", "license", "license_url", "snapshot_id")} | {
            "retrieval": "geographic filters + lexical BM25",
            "llm_configured": config.llm_configured,
            "service": "Telegis",
            "data_quality": {
                "with_opening_hours": sum(bool(p.opening_hours) for p in dataset.pois),
                "with_contacts": sum(bool(p.phone or p.website) for p in dataset.pois),
                "confirmed_features": {feature: sum(p.confirmed_features.get(feature) is True for p in dataset.pois)
                                       for feature in ("wifi", "socket", "quiet", "wheelchair")},
                "ratings_available": False,
            },
            "time_estimate": "one-way = max(1, ceil(straight_line_m * 1.3 / 70)) + 2; total = 2 * one-way + visit",
            "limitations": ["Расстояния по прямой; пешеходные маршруты не рассчитаны.",
                            "Часы и доступность в реальном времени не подтверждаются.",
                            "Точки крупных объектов могут быть центрами территории, а не входами.",
                            "Время посещения — эвристика по категории, не данные объекта.",
                            "Лексический поиск и правила понимают ограниченный набор условий."],
            "privacy": "Нет хранения запросов/GPS и аналитики; модели передаются выбранные POI и нормализованные ограничения, без исходного текста и координат пользователя.",
        }

    @api.post("/api/recommend", response_model=RecommendResponse)
    async def recommend(payload: RecommendRequest):
        dataset = store.get()
        result = retrieve(payload, dataset)
        context = UsedContext(**payload.model_dump(exclude={"query"}),
                              effective_minutes=result.effective_minutes, max_distance_m=result.max_distance_m,
                              required_features=list(result.required_features), excluded_categories=list(result.excluded_categories))
        if not result.candidates:
            return RecommendResponse(mode="fallback", used_context=context, recommendations=[], message=result.message)
        effective = payload.model_copy(update={"available_minutes": result.effective_minutes or payload.available_minutes})
        generated = await generator.generate(effective, result.candidates, result.required_features)
        recommendations = []
        for choice in generated.choices:
            candidate, poi = choice.candidate, choice.candidate.poi
            warnings = ["Расстояние по прямой; время приблизительное, пешеходный маршрут не рассчитан."]
            if poi.opening_hours:
                warnings.append("Расписание взято из OpenStreetMap; актуальность и доступность сейчас не подтверждены.")
            else:
                warnings.append("Часы работы не подтверждены.")
            if poi.coordinate_kind != "point":
                warnings.append("Координаты обозначают центр объекта, не проверенный вход.")
            collected = datetime.fromisoformat(poi.collected_at.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - collected).total_seconds() > 7 * 86400:
                warnings.append("Датасет собран более недели назад; сведения могли измениться.")
            recommendations.append(Recommendation(
                poi_id=poi.poi_id, name=poi.name, lat=poi.lat, lon=poi.lon, category=poi.category,
                distance_m=candidate.distance, walk_minutes_estimate=candidate.walk_minutes,
                visit_minutes_estimate=candidate.visit_minutes, total_minutes_estimate=candidate.total_minutes,
                why=choice.why, activity=choice.activity, opening_hours=poi.opening_hours,
                source_url=poi.source_url, collected_at=poi.collected_at, warnings=warnings,
                description=poi.description, phone=poi.phone, website=poi.website,
            ))
        return RecommendResponse(mode=generated.mode, used_context=context, recommendations=recommendations, message=generated.message)

    @api.get("/", include_in_schema=False)
    async def index():
        target = config.static_dir / "index.html"
        if target.is_file():
            return FileResponse(target)
        return JSONResponse({"service": "Telegis", "message": "Бэкенд Telegis готов. Добавьте static/index.html от участника 2.", "api_docs": "/docs"})

    api.mount("/static", OptionalStaticFiles(directory=str(config.static_dir), check_dir=False), name="static")
    return api


app = create_app()
