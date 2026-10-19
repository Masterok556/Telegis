from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    query: str = Field(min_length=1, max_length=1000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    available_minutes: int = Field(ge=10, le=180, strict=True)
    category: Literal["walk", "cafe"]


class UsedContext(BaseModel):
    lat: float
    lon: float
    available_minutes: int
    category: Literal["walk", "cafe"]
    effective_minutes: int | None = None
    max_distance_m: float = 2500
    required_features: list[str] = Field(default_factory=list)
    excluded_categories: list[str] = Field(default_factory=list)


class Location(BaseModel):
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class LocationsResponse(BaseModel):
    locations: list[Location]


class POI(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    poi_id: str
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    category: str
    description: str
    tags: dict[str, str]
    opening_hours: str | None
    source_url: str
    collected_at: str
    coordinate_kind: str
    confirmed_features: dict[str, bool | None]
    phone: str | None = None
    website: str | None = None

    @field_validator("website")
    @classmethod
    def website_is_public_http(cls, value: str | None) -> str | None:
        from urllib.parse import urlsplit
        if not value:
            return None
        try:
            parsed = urlsplit(value)
            if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
                return value
        except ValueError:
            pass
        return None

    @field_validator("source_url")
    @classmethod
    def source_is_osm(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"https://www\.openstreetmap\.org/(node|way|relation)/\d+", value):
            raise ValueError("Expected canonical OSM source URL")
        return value

    @field_validator("collected_at")
    @classmethod
    def timestamp_has_timezone(cls, value: str) -> str:
        from datetime import datetime
        if datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        return value


class Evidence(BaseModel):
    id: str
    text: str
    source_url: str
    collected_at: str
    kind: Literal["osm_tag", "official"]
    confidence: Literal["source_reported"] = "source_reported"
    published_at: str | None = None


class Recommendation(BaseModel):
    poi_id: str
    name: str
    lat: float
    lon: float
    category: str
    distance_m: int = Field(ge=0)
    distance_kind: Literal["straight_line"] = "straight_line"
    walk_minutes_estimate: int = Field(ge=0)
    visit_minutes_estimate: int = Field(ge=1)
    total_minutes_estimate: int = Field(ge=1)
    why: str
    activity: str
    opening_hours: str | None
    source_url: str
    collected_at: str
    warnings: list[str]
    description: str = ""
    phone: str | None = None
    website: str | None = None
    fact_source: Literal["OpenStreetMap", "OpenStreetMap + official sources"] = "OpenStreetMap"
    activity_source: Literal["suggested_idea"] = "suggested_idea"
    evidence: list[Evidence] = Field(default_factory=list)
    time_margin_minutes: int = Field(default=0, ge=0)
    travel_basis: Literal["straight_line_estimate", "osm_walking_graph"] = "straight_line_estimate"
    route_distance_m: int | None = None
    return_route_distance_m: int | None = None
    route_connector_m: int | None = None


class RecommendResponse(BaseModel):
    mode: Literal["rag", "fallback"]
    used_context: UsedContext
    recommendations: list[Recommendation] = Field(max_length=3)
    message: str
