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


class RecommendResponse(BaseModel):
    mode: Literal["rag", "fallback"]
    used_context: UsedContext
    recommendations: list[Recommendation] = Field(max_length=3)
    message: str
