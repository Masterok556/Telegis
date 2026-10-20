"""City-level model weather with explicit freshness and failure states.

The provider always receives the same public EXPO coordinate, never a request's
GPS, query, cookies or credentials. Current values are weather-model estimates,
not observations from a local station. See https://open-meteo.com/en/docs.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import math
from typing import Callable, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_SOURCE_URL = "https://open-meteo.com/en/docs"
WEATHER_LATITUDE = 51.089
WEATHER_LONGITUDE = 71.419
CURRENT_FIELDS = (
    "temperature_2m", "apparent_temperature", "precipitation", "weather_code",
    "wind_speed_10m", "wind_gusts_10m", "is_day",
)
WMO_CODES = {
    0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
    71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 97, 99,
}
RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
FREEZING_CODES = {56, 57, 66, 67}
THUNDER_CODES = {95, 96, 97, 99}


class WeatherLocation(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str = "Астана · EXPO"
    lat: float = WEATHER_LATITUDE
    lon: float = WEATHER_LONGITUDE
    kind: Literal["fixed_area"] = "fixed_area"


class WeatherCurrent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    temperature_c: float = Field(ge=-100, le=70)
    apparent_temperature_c: float = Field(ge=-120, le=80)
    wind_m_s: float = Field(ge=0, le=120)
    gust_m_s: float = Field(ge=0, le=150)
    precipitation_mm: float = Field(ge=0, le=500)
    precipitation_interval_seconds: int = Field(ge=60, le=3600)
    weather_code: int
    is_day: bool


class ClimatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    mode: Literal["normal", "prefer_indoor", "avoid_outdoor", "unknown"]
    reasons: list[str] = Field(default_factory=list)
    message: str


class WeatherSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: Literal["live", "stale", "unavailable", "demo"]
    source: str
    source_url: str | None
    location: WeatherLocation = Field(default_factory=WeatherLocation)
    valid_at: datetime | None
    fetched_at: datetime | None
    age_seconds: int | None
    current: WeatherCurrent | None
    policy: ClimatePolicy
    warnings: list[str] = Field(default_factory=list)
    attribution: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def climate_policy(current: WeatherCurrent) -> ClimatePolicy:
    """Transparent product comfort rules, not official alerts or safety advice.

    These rules describe outdoor exposure. They cannot prove that a POI is
    indoors, heated, open or reachable through covered walking paths.
    """
    severe: list[str] = []
    moderate: list[str] = []
    feels_like = current.apparent_temperature_c
    if feels_like <= -20:
        severe.append("extreme_cold")
    elif feels_like <= -10:
        moderate.append("cold")
    if feels_like >= 40:
        severe.append("extreme_heat")
    elif feels_like >= 32:
        moderate.append("heat")
    if current.wind_m_s >= 15 or current.gust_m_s >= 20:
        severe.append("extreme_wind")
    elif current.wind_m_s >= 10 or current.gust_m_s >= 15:
        moderate.append("strong_wind")
    if current.weather_code in THUNDER_CODES:
        severe.append("thunderstorm")
    if current.weather_code in FREEZING_CODES:
        severe.append("freezing_precipitation")
    if current.weather_code in SNOW_CODES:
        moderate.append("snow")
    elif current.weather_code in RAIN_CODES or current.precipitation_mm >= 0.2:
        moderate.append("precipitation")
    if severe:
        return ClimatePolicy(
            mode="avoid_outdoor", reasons=severe + moderate,
            message="Модельные условия неблагоприятны для пешей прогулки. "
                    "Климатический режим не предлагает маршрут с уличными переходами; "
                    "проверьте местный прогноз и официальные предупреждения.",
        )
    if moderate:
        return ClimatePolicy(
            mode="prefer_indoor", reasons=moderate,
            message="Для климатического режима подходят только места с подтверждением помещения. "
                    "Переходы до них остаются уличными; тепло, часы и текущая доступность не подтверждаются.",
        )
    return ClimatePolicy(
        mode="normal", reasons=[],
        message="Порогов климатического режима по этим модельным данным не обнаружено. "
                "Это не подтверждение безопасности, проходимости или неизменности погоды.",
    )


def unknown_policy(reason: str) -> ClimatePolicy:
    return ClimatePolicy(
        mode="unknown", reasons=[reason],
        message="Актуальных погодных данных недостаточно для климатической адаптации.",
    )


def demo_snapshot() -> WeatherSnapshot:
    """An explicitly requested synthetic scenario; never enters the live cache."""
    current = WeatherCurrent(
        temperature_c=-12, apparent_temperature_c=-18, wind_m_s=10,
        gust_m_s=15, precipitation_mm=0, precipitation_interval_seconds=900,
        weather_code=3, is_day=True,
    )
    return WeatherSnapshot(
        status="demo", source="Telegis demo", source_url=None,
        valid_at=None, fetched_at=None, age_seconds=None, current=current,
        policy=climate_policy(current),
        warnings=["Демонстрационный сценарий с вымышленной погодой. "
                  "Это не текущие данные Астаны и не ответ Open-Meteo."],
        attribution="Telegis: синтетический демонстрационный сценарий.",
    )


def _number(value: object, name: str, low: float, high: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Invalid {name}")
    return float(value)


def parse_weather(payload: object, fetched_at: datetime, *, max_age_seconds: int = 21600) -> WeatherSnapshot:
    """Reject bad units, missing values, ancient/future timestamps and fake zeros."""
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("Invalid weather object")
    current, units = payload.get("current"), payload.get("current_units")
    if not isinstance(current, dict) or not isinstance(units, dict):
        raise ValueError("Missing current weather")
    expected_units = {
        "time": "unixtime", "interval": "seconds",
        "temperature_2m": "°C", "apparent_temperature": "°C",
        "wind_speed_10m": "m/s", "wind_gusts_10m": "m/s",
        "precipitation": "mm", "weather_code": "wmo code", "is_day": "",
    }
    if any(units.get(key) != value for key, value in expected_units.items()):
        raise ValueError("Unexpected weather units")
    timestamp = current.get("time")
    if type(timestamp) is not int:
        raise ValueError("Invalid weather timestamp")
    try:
        valid_at = datetime.fromtimestamp(timestamp, timezone.utc)
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError("Invalid weather timestamp") from exc
    age = (fetched_at - valid_at).total_seconds()
    if age < -300 or age > max_age_seconds:
        raise ValueError("Weather timestamp is outside the accepted time window")
    interval, code, is_day = current.get("interval"), current.get("weather_code"), current.get("is_day")
    if type(interval) is not int or not 60 <= interval <= 3600:
        raise ValueError("Invalid accumulation interval")
    if type(code) is not int or code not in WMO_CODES:
        raise ValueError("Unknown WMO weather code")
    if type(is_day) is not int or is_day not in (0, 1):
        raise ValueError("Invalid day/night field")
    values = WeatherCurrent(
        temperature_c=_number(current.get("temperature_2m"), "temperature", -100, 70),
        apparent_temperature_c=_number(current.get("apparent_temperature"), "apparent temperature", -120, 80),
        wind_m_s=_number(current.get("wind_speed_10m"), "wind", 0, 120),
        gust_m_s=_number(current.get("wind_gusts_10m"), "wind gust", 0, 150),
        precipitation_mm=_number(current.get("precipitation"), "precipitation", 0, 500),
        precipitation_interval_seconds=interval,
        weather_code=code, is_day=bool(is_day),
    )
    return WeatherSnapshot(
        status="live", source="Open-Meteo", source_url=WEATHER_SOURCE_URL,
        valid_at=valid_at, fetched_at=fetched_at, age_seconds=max(0, int(age)),
        current=values, policy=climate_policy(values),
        warnings=[
            "Погода — модельная оценка для района EXPO, а не измерение у вашей точки.",
            f"Осадки указаны в мм за предыдущие {interval // 60} мин, а не в мм/ч.",
            "Текущие условия не являются прогнозом на всё время прогулки.",
            "Пороговые правила Telegis служат выбору формата прогулки и не заменяют официальные предупреждения.",
        ],
        attribution="Weather data: Open-Meteo · CC BY 4.0",
    )


class WeatherService:
    """One bounded async cache per public city area, with request coalescing."""

    def __init__(
        self, *, enabled: bool = True, timeout_seconds: float = 4.0,
        cache_seconds: int = 900, fresh_seconds: int = 2700,
        stale_seconds: int = 21600, retry_seconds: int = 120,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], datetime] = utc_now,
    ):
        if not 0 < timeout_seconds <= 15:
            raise ValueError("Weather timeout must be between 0 and 15 seconds")
        if min(cache_seconds, fresh_seconds, stale_seconds, retry_seconds) <= 0:
            raise ValueError("Weather cache durations must be positive")
        if fresh_seconds > stale_seconds:
            raise ValueError("Fresh weather window cannot exceed stale window")
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.cache_seconds = cache_seconds
        self.fresh_seconds = fresh_seconds
        self.stale_seconds = stale_seconds
        self.retry_seconds = retry_seconds
        self._transport = transport
        self._clock = clock
        self._snapshot: WeatherSnapshot | None = None
        self._next_attempt: datetime | None = None
        self._failure: str | None = None
        self._lock = asyncio.Lock()

    def _fresh(self, now: datetime) -> bool:
        item = self._snapshot
        if item is None or item.valid_at is None or item.fetched_at is None:
            return False
        return (0 <= (now - item.fetched_at).total_seconds() < self.cache_seconds
                and -300 <= (now - item.valid_at).total_seconds() <= self.fresh_seconds
                and self._failure is None)

    def _result(self, now: datetime, *, reason: str | None = None) -> WeatherSnapshot:
        item = self._snapshot
        if reason != "weather_disabled" and item is not None and item.valid_at is not None:
            age = (now - item.valid_at).total_seconds()
            if -300 <= age <= self.stale_seconds:
                if self._fresh(now):
                    return item.model_copy(update={"age_seconds": max(0, int(age))}, deep=True)
                return item.model_copy(update={
                    "status": "stale", "age_seconds": max(0, int(age)),
                    "policy": unknown_policy("stale_weather"),
                    "warnings": item.warnings + [
                        "Показаны устаревшие сведения, не погода сейчас. Климатическая адаптация по ним не применяется."
                    ],
                }, deep=True)
        return WeatherSnapshot(
            status="unavailable", source="Open-Meteo", source_url=WEATHER_SOURCE_URL,
            valid_at=None, fetched_at=None, age_seconds=None, current=None,
            policy=unknown_policy(reason or self._failure or "weather_unavailable"),
            warnings=["Текущую погоду получить не удалось. Значения не подставлены; климатическая адаптация недоступна."],
            attribution="Weather data provider: Open-Meteo · CC BY 4.0",
        )

    async def _fetch(self, now: datetime) -> WeatherSnapshot:
        params = {
            "latitude": str(WEATHER_LATITUDE), "longitude": str(WEATHER_LONGITUDE),
            "current": ",".join(CURRENT_FIELDS), "temperature_unit": "celsius",
            "wind_speed_unit": "ms", "precipitation_unit": "mm",
            "timeformat": "unixtime", "timezone": "GMT", "forecast_days": "1",
        }
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, transport=self._transport,
            follow_redirects=False, headers={"User-Agent": "Telegis/1.0 (public EXPO area weather)"},
        ) as client:
            async with client.stream("GET", WEATHER_URL, params=params) as response:
                response.raise_for_status()
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 128_000:
                        raise ValueError("Weather response exceeds size limit")
                    chunks.append(chunk)
                import json
                payload = json.loads(b"".join(chunks))
        return parse_weather(
            payload, self._clock().astimezone(timezone.utc),
            max_age_seconds=self.stale_seconds,
        )

    async def get(self, demo: bool = False) -> WeatherSnapshot:
        if demo:
            return demo_snapshot()
        now = self._clock().astimezone(timezone.utc)
        if not self.enabled:
            return self._result(now, reason="weather_disabled")
        if self._fresh(now):
            return self._result(now)
        if (not self._lock.locked() and self._next_attempt is not None
                and now < self._next_attempt):
            return self._result(now)
        async with self._lock:
            now = self._clock().astimezone(timezone.utc)
            if self._fresh(now) or (self._next_attempt is not None and now < self._next_attempt):
                return self._result(now)
            self._next_attempt = now + timedelta(seconds=self.retry_seconds)
            try:
                self._snapshot = await self._fetch(now)
                self._failure = None
                self._next_attempt = now + timedelta(seconds=self.cache_seconds)
            except httpx.TimeoutException:
                self._failure = "provider_timeout"
            except httpx.HTTPError:
                self._failure = "provider_unavailable"
            except (ValueError, TypeError, KeyError):
                self._failure = "invalid_provider_response"
            return self._result(self._clock().astimezone(timezone.utc))
