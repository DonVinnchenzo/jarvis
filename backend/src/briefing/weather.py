"""Fetch current weather from Open-Meteo API."""

import logging
from dataclasses import dataclass

import httpx

from src.briefing.constants import (
    API_TIMEOUT_SECONDS,
    WEATHER_API_URL,
    WEATHER_PARAMS,
    WMO_WEATHER_CODES,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherData:
    """Structured weather data for the morning briefing."""

    # Current conditions
    temperature: float          # Celsius
    feels_like: float           # Celsius
    precipitation: float        # mm
    wind_speed: float           # km/h
    wind_gusts: float           # km/h
    humidity: int               # percent
    weather_code: int           # WMO code
    weather_description: str    # Human-readable from WMO code

    # Daily forecast
    high: float                 # Celsius
    low: float                  # Celsius
    feels_like_high: float      # Celsius
    feels_like_low: float       # Celsius
    precip_probability: int     # percent (0-100)
    daily_max_wind: float       # km/h
    daily_weather_code: int     # WMO code
    daily_weather_description: str  # Human-readable from daily WMO code


async def fetch_weather() -> WeatherData | None:
    """Fetch weather data from Open-Meteo. Returns None on any failure.

    Uses a 10-second httpx timeout. Logs errors but never raises.
    """
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
            resp = await client.get(WEATHER_API_URL, params=WEATHER_PARAMS)
            resp.raise_for_status()
            data = resp.json()

        current = data["current"]
        daily = data["daily"]

        return WeatherData(
            temperature=current["temperature_2m"],
            feels_like=current["apparent_temperature"],
            precipitation=current["precipitation"],
            wind_speed=current["wind_speed_10m"],
            wind_gusts=current["wind_gusts_10m"],
            humidity=current["relative_humidity_2m"],
            weather_code=current["weather_code"],
            weather_description=WMO_WEATHER_CODES.get(
                current["weather_code"], "Unknown"
            ),
            high=daily["temperature_2m_max"][0],
            low=daily["temperature_2m_min"][0],
            feels_like_high=daily["apparent_temperature_max"][0],
            feels_like_low=daily["apparent_temperature_min"][0],
            precip_probability=daily["precipitation_probability_max"][0],
            daily_max_wind=daily["wind_speed_10m_max"][0],
            daily_weather_code=daily["weather_code"][0],
            daily_weather_description=WMO_WEATHER_CODES.get(
                daily["weather_code"][0], "Unknown"
            ),
        )

    except httpx.TimeoutException:
        logger.error("Weather API timed out after %ds", API_TIMEOUT_SECONDS)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Weather API returned HTTP %d: %s", e.response.status_code, e.response.text[:200])
        return None
    except (KeyError, IndexError, TypeError) as e:
        logger.error("Weather API returned unexpected data structure: %s", e)
        return None
    except Exception:
        logger.exception("Unexpected error fetching weather")
        return None
