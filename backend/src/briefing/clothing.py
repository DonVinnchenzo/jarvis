"""Clothing suggestion based on weather conditions, optimized for biking."""

from src.briefing.constants import (
    CLOTHING_BRUTAL,
    CLOTHING_RAIN,
    CLOTHING_THRESHOLDS,
    CLOTHING_WIND,
)
from src.briefing.weather import WeatherData


def get_clothing_suggestion(weather: WeatherData) -> str:
    """Return a clothing suggestion string based on weather conditions.

    Uses feels-like temperature as the primary driver, with rain and wind modifiers.
    Pure function -- no side effects.
    """
    feels = weather.feels_like

    # Base suggestion from feels-like temperature
    base = CLOTHING_BRUTAL  # default: below all thresholds
    for threshold_temp, suggestion in CLOTHING_THRESHOLDS:
        if feels >= threshold_temp:
            base = suggestion
            break

    parts = [base]

    # Rain modifier: current precipitation, high probability, or rain code in
    # either current or daily forecast. The morning briefing dresses you for
    # the whole day, not just the moment.
    rain_codes = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
    has_rain = (
        weather.precipitation > 0
        or weather.precip_probability > 60
        or weather.weather_code in rain_codes
        or weather.daily_weather_code in rain_codes
    )
    if has_rain:
        parts.append(CLOTHING_RAIN)

    # Wind modifier
    if weather.wind_speed > 15:
        parts.append(CLOTHING_WIND)

    return "\n".join(parts)
