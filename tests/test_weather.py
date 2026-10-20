"""Model weather freshness, failure isolation and public-coordinate privacy."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.weather import (
    WeatherCurrent, WeatherService, climate_policy, demo_snapshot, parse_weather,
    WEATHER_LATITUDE, WEATHER_LONGITUDE,
)


NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def provider_payload(**updates):
    current = {
        "time": int((NOW - timedelta(minutes=15)).timestamp()),
        "interval": 900, "temperature_2m": 12.0, "apparent_temperature": 10.0,
        "precipitation": 0.0, "weather_code": 2, "wind_speed_10m": 3.2,
        "wind_gusts_10m": 5.0, "is_day": 1,
    }
    current.update(updates)
    return {
        "latitude": 51.1, "longitude": 71.4,
        "current_units": {
            "time": "unixtime", "interval": "seconds",
            "temperature_2m": "°C", "apparent_temperature": "°C",
            "precipitation": "mm", "weather_code": "wmo code",
            "wind_speed_10m": "m/s", "wind_gusts_10m": "m/s", "is_day": "",
        },
        "current": current,
    }


def service(handler, clock=lambda: NOW, **kwargs):
    return WeatherService(transport=httpx.MockTransport(handler), clock=clock, **kwargs)


def test_live_model_weather_has_provider_time_units_and_fixed_public_area():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=provider_payload())
    weather = asyncio.run(service(handler).get())
    assert weather.status == "live" and weather.source == "Open-Meteo"
    assert weather.valid_at == NOW - timedelta(minutes=15)
    assert weather.fetched_at == NOW and weather.age_seconds == 900
    assert weather.current.temperature_c == 12
    assert weather.current.wind_m_s == 3.2
    assert weather.current.precipitation_interval_seconds == 900
    assert weather.policy.mode == "normal"
    assert weather.location.kind == "fixed_area"
    assert "модельная" in weather.warnings[0]
    request = requests[0]
    assert request.url.host == "api.open-meteo.com"
    assert request.url.params["latitude"] == str(WEATHER_LATITUDE)
    assert request.url.params["longitude"] == str(WEATHER_LONGITUDE)
    assert request.url.params["wind_speed_unit"] == "ms"
    assert request.url.params["timeformat"] == "unixtime"
    assert "authorization" not in request.headers and "cookie" not in request.headers
    assert not request.content


def test_fetched_at_is_completion_time_not_start_of_slow_request():
    now = [NOW]
    def handler(request):
        now[0] += timedelta(seconds=3)
        return httpx.Response(200, json=provider_payload())
    weather = asyncio.run(service(handler, clock=lambda: now[0]).get())
    assert weather.fetched_at == NOW + timedelta(seconds=3)
    assert weather.age_seconds == 903


def test_cache_coalesces_simultaneous_requests_and_does_not_share_mutable_lists():
    calls = []
    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json=provider_payload())
    async def run():
        client = service(handler)
        values = await asyncio.gather(*(client.get() for _ in range(8)))
        values[0].warnings.append("caller change")
        another = await client.get()
        return values, another
    values, another = asyncio.run(run())
    assert len(calls) == 1
    assert all(w.status == "live" for w in values)
    assert "caller change" not in another.warnings


def test_failure_preserves_stale_original_timestamps_without_climate_policy():
    now, calls = [NOW], []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json=provider_payload())
        raise httpx.ReadTimeout("provider timeout", request=request)
    async def run():
        client = service(handler, clock=lambda: now[0])
        first = await client.get()
        now[0] += timedelta(minutes=16)
        stale = await client.get()
        again = await client.get()
        return first, stale, again
    first, stale, again = asyncio.run(run())
    assert len(calls) == 2
    assert stale.status == again.status == "stale"
    assert stale.current == first.current
    assert stale.fetched_at == first.fetched_at
    assert stale.valid_at == first.valid_at
    assert stale.age_seconds == 31 * 60
    assert stale.policy.mode == "unknown"
    assert stale.policy.reasons == ["stale_weather"]
    assert "не погода сейчас" in stale.warnings[-1]


def test_expired_stale_value_becomes_null_and_never_demo():
    now, calls = [NOW], []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json=provider_payload())
        return httpx.Response(503)
    async def run():
        client = service(handler, clock=lambda: now[0])
        await client.get()
        now[0] += timedelta(hours=7)
        return await client.get()
    weather = asyncio.run(run())
    assert weather.status == "unavailable"
    assert weather.current is weather.valid_at is weather.fetched_at is None
    assert weather.policy.mode == "unknown"


def test_initial_failure_backoff_then_success():
    calls, now = [], [NOW]
    def handler(request):
        calls.append(request)
        return httpx.Response(502) if len(calls) == 1 else httpx.Response(200, json=provider_payload())
    async def run():
        client = service(handler, clock=lambda: now[0])
        first = await client.get()
        now[0] += timedelta(seconds=119)
        second = await client.get()
        now[0] += timedelta(seconds=2)
        third = await client.get()
        return first, second, third
    first, second, third = asyncio.run(run())
    assert first.status == second.status == "unavailable"
    assert first.current is None
    assert third.status == "live" and len(calls) == 2


def test_old_but_usable_provider_timestep_is_stale_even_after_successful_fetch():
    weather = asyncio.run(service(lambda _: httpx.Response(
        200, json=provider_payload(time=int((NOW - timedelta(hours=2)).timestamp())),
    )).get())
    assert weather.status == "stale"
    assert weather.fetched_at == NOW
    assert weather.policy.mode == "unknown"


def test_demo_is_explicit_synthetic_and_never_contaminates_provider_cache():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=provider_payload())
    async def run():
        client = service(handler)
        demo = await client.get(demo=True)
        real = await client.get()
        demo_again = await client.get(demo=True)
        cached = await client.get()
        return demo, real, demo_again, cached
    demo, real, demo_again, cached = asyncio.run(run())
    assert demo.status == demo_again.status == "demo"
    assert demo.source == "Telegis demo" and demo.source_url is None
    assert demo.valid_at is demo.fetched_at is demo.age_seconds is None
    assert demo.policy.mode == "prefer_indoor"
    assert real.status == cached.status == "live"
    assert real.current.temperature_c == 12
    assert len(calls) == 1


def test_disabled_service_does_not_make_network_requests():
    def handler(_):
        pytest.fail("Disabled service must not call the provider")
    weather = asyncio.run(service(handler, enabled=False).get())
    assert weather.status == "unavailable" and weather.current is None
    assert weather.policy.reasons == ["weather_disabled"]


@pytest.mark.parametrize("mutate", [
    lambda p: p["current"].pop("temperature_2m"),
    lambda p: p["current"].update(temperature_2m=None),
    lambda p: p["current"].update(temperature_2m="12"),
    lambda p: p["current"].update(temperature_2m=True),
    lambda p: p["current"].update(temperature_2m=float("nan")),
    lambda p: p["current"].update(wind_speed_10m=-1),
    lambda p: p["current"].update(weather_code=1000),
    lambda p: p["current"].update(is_day=True),
    lambda p: p["current"].update(interval=0),
    lambda p: p["current"].update(time=int((NOW + timedelta(minutes=6)).timestamp())),
    lambda p: p["current"].update(time=int((NOW - timedelta(hours=7)).timestamp())),
    lambda p: p["current_units"].update(wind_speed_10m="km/h"),
    lambda p: p["current_units"].update(precipitation="inch"),
])
def test_invalid_or_incomplete_provider_data_is_rejected(mutate):
    payload = deepcopy(provider_payload())
    mutate(payload)
    with pytest.raises(ValueError):
        parse_weather(payload, NOW)


@pytest.mark.parametrize("response", [
    httpx.Response(200, json={"error": True, "reason": "bad request"}),
    httpx.Response(200, content=b"not JSON"),
    httpx.Response(200, content=b"x" * 128001),
    httpx.Response(302, headers={"location": "https://other.example/weather"}),
])
def test_invalid_http_response_does_not_fabricate_current_weather(response):
    weather = asyncio.run(service(lambda _: response).get())
    assert weather.status == "unavailable"
    assert weather.current is None and weather.policy.mode == "unknown"


def comfortable_weather(**updates):
    return WeatherCurrent(**{
        "temperature_c": 12, "apparent_temperature_c": 10,
        "wind_m_s": 3, "gust_m_s": 5,
        "precipitation_mm": 0, "precipitation_interval_seconds": 900,
        "weather_code": 2, "is_day": True,
    } | updates)


@pytest.mark.parametrize("changes,mode,reason", [
    ({"apparent_temperature_c": -10}, "prefer_indoor", "cold"),
    ({"apparent_temperature_c": -20}, "avoid_outdoor", "extreme_cold"),
    ({"apparent_temperature_c": 32}, "prefer_indoor", "heat"),
    ({"apparent_temperature_c": 40}, "avoid_outdoor", "extreme_heat"),
    ({"wind_m_s": 10}, "prefer_indoor", "strong_wind"),
    ({"gust_m_s": 20}, "avoid_outdoor", "extreme_wind"),
    ({"precipitation_mm": 0.2}, "prefer_indoor", "precipitation"),
    ({"weather_code": 71}, "prefer_indoor", "snow"),
    ({"weather_code": 66}, "avoid_outdoor", "freezing_precipitation"),
    ({"weather_code": 95}, "avoid_outdoor", "thunderstorm"),
])
def test_transparent_climate_thresholds(changes, mode, reason):
    policy = climate_policy(comfortable_weather(**changes))
    assert policy.mode == mode and reason in policy.reasons


def test_normal_weather_never_claims_route_safety():
    policy = climate_policy(comfortable_weather())
    assert policy.mode == "normal" and policy.reasons == []
    assert "не подтверждение безопасности" in policy.message
    assert "вымышленной" in demo_snapshot().warnings[0]
