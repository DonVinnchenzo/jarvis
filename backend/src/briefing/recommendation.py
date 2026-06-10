"""Biking recommendation: should the user bike today?"""

from src.briefing.constants import (
    BIKE_MAX_FEELS_LIKE,
    BIKE_MAX_WIND_SPEED,
    BIKE_MIN_FEELS_LIKE,
    PRECIPITATION_WEATHER_CODES,
)
from src.briefing.divvy import DivvyData
from src.briefing.weather import WeatherData


def get_bike_recommendation(
    weather: WeatherData | None,
    divvy: DivvyData | None,
) -> tuple[bool, str]:
    """Return (should_bike: bool, reason: str).

    Checks weather conditions and bike availability.
    Pure function -- no side effects.
    """
    if weather is None and divvy is None:
        return False, "Data unavailable \u2014 check manually."

    reasons_no: list[str] = []

    # --- Weather checks ---
    if weather is not None:
        # Rain / storm check — consider both current and daily forecast.
        # A morning briefing decides the whole day, so a thunderstorm forecast
        # later today must block the recommendation even when it's clear now.
        current_precip = (
            weather.precipitation > 0
            or weather.weather_code in PRECIPITATION_WEATHER_CODES
        )
        daily_precip = weather.daily_weather_code in PRECIPITATION_WEATHER_CODES
        rain_likely = weather.precip_probability > 60

        if current_precip:
            reasons_no.append("rain expected all morning")
        elif daily_precip:
            reasons_no.append(f"{weather.daily_weather_description.lower()} forecast today")
        elif rain_likely:
            reasons_no.append(f"{weather.precip_probability}% chance of rain")

        # Temperature check
        if weather.feels_like < BIKE_MIN_FEELS_LIKE:
            reasons_no.append(f"feels like {weather.feels_like:.0f}\u00b0C \u2014 dangerously cold")
        elif weather.feels_like > BIKE_MAX_FEELS_LIKE:
            reasons_no.append(f"feels like {weather.feels_like:.0f}\u00b0C \u2014 dangerously hot")

        # Wind check
        if weather.wind_speed >= BIKE_MAX_WIND_SPEED:
            reasons_no.append(f"wind at {weather.wind_speed:.0f} km/h")

    # --- Bike availability checks ---
    if divvy is not None and divvy.home_primary is not None:
        home = divvy.home_primary
        if not home.is_active:
            reasons_no.append("home station temporarily unavailable")
        elif home.total_vehicles == 0:
            # Check backup station and free-floating
            backup_ok = (
                divvy.home_backup is not None
                and divvy.home_backup.is_active
                and divvy.home_backup.total_vehicles > 0
            )
            free_ok = (divvy.nearby_free.ebikes + divvy.nearby_free.scooters) > 0
            if not backup_ok and not free_ok:
                reasons_no.append("no bikes available at home or nearby")
    elif divvy is None:
        # Divvy data unavailable -- don't block on it
        pass

    if reasons_no:
        return False, " and ".join(reasons_no)

    return True, "great conditions and bikes available!"
