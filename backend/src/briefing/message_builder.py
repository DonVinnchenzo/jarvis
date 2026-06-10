"""Build morning briefing Telegram messages."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.briefing.clothing import get_clothing_suggestion
from src.briefing.constants import (
    BRIEFING_TIMEZONE,
    OFFICE_BY_NAME,
    PRECIPITATION_WEATHER_CODES,
    STATION_NAMES,
    STATIONS,
)
from src.briefing.divvy import DivvyData, StationAvailability
from src.briefing.recommendation import get_bike_recommendation
from src.briefing.weather import WeatherData

logger = logging.getLogger(__name__)

# Weather code to emoji mapping (simplified)
_WEATHER_EMOJIS: dict[int, str] = {
    0: "\u2600\ufe0f",      # Clear sky -> sun
    1: "\U0001f324\ufe0f",  # Mainly clear
    2: "\u26c5",             # Partly cloudy
    3: "\u2601\ufe0f",      # Overcast
    45: "\U0001f32b\ufe0f", # Fog
    48: "\U0001f32b\ufe0f", # Rime fog
}
# Rain/snow/storm codes all map to appropriate emoji
for _code in range(51, 100):
    if _code not in _WEATHER_EMOJIS:
        if _code in {71, 73, 75, 77, 85, 86}:
            _WEATHER_EMOJIS[_code] = "\u2744\ufe0f"   # Snow
        elif _code in {95, 96, 99}:
            _WEATHER_EMOJIS[_code] = "\u26a1"          # Thunder
        else:
            _WEATHER_EMOJIS[_code] = "\U0001f327\ufe0f"  # Rain


def _greeting_emoji(weather: WeatherData | None) -> str:
    """Pick a greeting emoji based on current weather."""
    if weather is None:
        return "\U0001f44b"  # wave
    return _WEATHER_EMOJIS.get(weather.weather_code, "\u2600\ufe0f")


def _format_weather_section(weather: WeatherData) -> str:
    """Format the weather section of the briefing."""
    description = weather.weather_description

    # If the daily forecast indicates precipitation but right now is clear,
    # surface the daily forecast \u2014 readers decide the whole day from this line.
    daily_is_precip = weather.daily_weather_code in PRECIPITATION_WEATHER_CODES
    current_is_precip = weather.weather_code in PRECIPITATION_WEATHER_CODES
    if daily_is_precip and not current_is_precip:
        description = f"{description}, {weather.daily_weather_description.lower()} forecast"

    emoji_line = (
        f"\U0001f321 Weather: {weather.temperature:.0f}\u00b0C "
        f"(feels like {weather.feels_like:.0f}\u00b0C)"
    )
    range_line = f"\u2191 High {weather.high:.0f}\u00b0C / \u2193 Low {weather.low:.0f}\u00b0C"
    detail_line = (
        f"{description} \u2022 {weather.precip_probability}% chance of rain "
        f"\u2022 Wind {weather.wind_speed:.0f} km/h"
    )
    return f"{emoji_line}\n{range_line}\n{detail_line}"


def _format_station_bikes(station: StationAvailability, station_name: str, label: str) -> str:
    """Format a bike station section (for home station)."""
    if not station.is_active:
        return f"\U0001f6b2 Bikes at {station_name} ({label}):\n   Station temporarily unavailable"

    parts = []
    if station.ebikes > 0:
        parts.append(f"{station.ebikes} ebike{'s' if station.ebikes != 1 else ''}")
    if station.scooters > 0:
        parts.append(f"{station.scooters} scooter{'s' if station.scooters != 1 else ''}")
    if station.classic_bikes > 0:
        parts.append(f"{station.classic_bikes} classic bike{'s' if station.classic_bikes != 1 else ''}")

    if not parts:
        parts.append("0 bikes available")

    vehicles_str = " \u2022 ".join(parts)
    return f"\U0001f6b2 Bikes at {station_name} ({label}):\n   {vehicles_str}"


def _format_station_docks(station: StationAvailability, station_name: str, office_label: str) -> str:
    """Format a dock station section (for office stations)."""
    if not station.is_active:
        return f"\U0001f4cd Docks at {station_name} ({office_label}):\n   Station temporarily unavailable"

    docks = station.docks_available
    if docks == 0:
        desc = "FULL \u2014 no empty docks, find another station nearby"
    elif docks <= 3:
        desc = f"{docks} empty dock{'s' if docks != 1 else ''} \u2014 almost full, hurry!"
    else:
        desc = f"{docks} empty docks \u2014 plenty of room"

    return f"\U0001f4cd Docks at {station_name} ({office_label}):\n   {desc}"


def _format_backup_note(divvy: DivvyData) -> str:
    """If home primary has no ebikes/scooters, mention backup station and free-floating."""
    parts: list[str] = []

    home = divvy.home_primary
    if home is None or (home.ebikes + home.scooters) > 0:
        return ""  # No need for backup info

    # Check backup station
    if divvy.home_backup and divvy.home_backup.is_active:
        backup = divvy.home_backup
        backup_name = STATION_NAMES.get(STATIONS["home"]["backup"], "backup station")
        if backup.ebikes > 0 or backup.scooters > 0:
            vehicles = []
            if backup.ebikes > 0:
                vehicles.append(f"{backup.ebikes} ebike{'s' if backup.ebikes != 1 else ''}")
            if backup.scooters > 0:
                vehicles.append(f"{backup.scooters} scooter{'s' if backup.scooters != 1 else ''}")
            parts.append(f"\U0001f504 Backup ({backup_name}): {', '.join(vehicles)}")

    # Check free-floating
    free = divvy.nearby_free
    if free.ebikes > 0 or free.scooters > 0:
        vehicles = []
        if free.ebikes > 0:
            vehicles.append(f"{free.ebikes} ebike{'s' if free.ebikes != 1 else ''}")
        if free.scooters > 0:
            vehicles.append(f"{free.scooters} scooter{'s' if free.scooters != 1 else ''}")
        parts.append(f"\U0001f504 Nearby free-floating: {', '.join(vehicles)}")

    return "\n".join(parts)


def _format_recommendation(should_bike: bool, reason: str) -> str:
    """Format the bike recommendation line."""
    if should_bike:
        return f"\u2705 Bike today? Yes \u2014 {reason}"
    return f"\u274c Bike today? Probably not \u2014 {reason}."


def build_briefing_message(
    user_name: str,
    weather: WeatherData | None,
    divvy: DivvyData | None,
    todays_events: list[str] | None = None,
) -> str:
    """Build a complete morning briefing message for a specific user.

    Handles partial failure: if weather is None, omit weather section.
    If divvy is None, omit Divvy section. Always sends something.

    Args:
        user_name: Display name ("Vincent" or "Christianne")
        weather: Weather data or None if API failed
        divvy: Divvy data or None if API failed
        todays_events: List of Social Circle event strings for today (cross-module)
    """
    greeting_emoji = _greeting_emoji(weather)
    lines: list[str] = [f"Good morning {user_name}! {greeting_emoji}"]

    # --- Weather section ---
    if weather is not None:
        lines.append("")
        lines.append(_format_weather_section(weather))
        lines.append("")
        lines.append(f"\U0001f454 {get_clothing_suggestion(weather)}")
    else:
        lines.append("")
        lines.append("\u26a0\ufe0f Weather data unavailable.")

    # --- Divvy section ---
    if divvy is not None:
        home_name = STATION_NAMES.get(STATIONS["home"]["primary"], "home station")

        # Home station bikes
        if divvy.home_primary is not None:
            lines.append("")
            lines.append(_format_station_bikes(divvy.home_primary, home_name, "home"))

            # Backup note if no ebikes/scooters at home
            backup_note = _format_backup_note(divvy)
            if backup_note:
                lines.append(backup_note)
        else:
            lines.append("")
            lines.append(f"\U0001f6b2 Bikes at {home_name} (home):\n   Data unavailable")

        # Office station docks (per-user)
        office_info = OFFICE_BY_NAME.get(user_name)
        if office_info:
            office_station_id = office_info["station_id"]
            office_label = office_info["label"]
            office_name = STATION_NAMES.get(office_station_id, "office")

            if user_name == "Vincent":
                station = divvy.optiver_dropoff
            else:
                station = divvy.adyen_dropoff

            if station is not None:
                lines.append("")
                lines.append(_format_station_docks(station, office_name, office_label))
            else:
                lines.append("")
                lines.append(f"\U0001f4cd Docks at {office_name} ({office_label}):\n   Data unavailable")
    else:
        lines.append("")
        lines.append("\u26a0\ufe0f Bike data unavailable.")

    # --- Biking recommendation ---
    should_bike, reason = get_bike_recommendation(weather, divvy)
    lines.append("")
    lines.append(_format_recommendation(should_bike, reason))

    # --- Social Circle events for today (cross-module) ---
    if todays_events:
        lines.append("")
        lines.append("\U0001f4c5 Today:")
        for event_str in todays_events:
            lines.append(f"   \u2022 {event_str}")

    return "\n".join(lines)


def build_on_demand_bikes_message(divvy: DivvyData | None) -> str:
    """Build a shorter message for on-demand bike status check."""
    if divvy is None:
        return "\u26a0\ufe0f Couldn't fetch bike data right now. Try again in a minute."

    now_str = datetime.now(ZoneInfo(BRIEFING_TIMEZONE)).strftime("%I:%M %p")
    lines = [f"\U0001f6b2 Divvy status ({now_str} CT)"]

    home_name = STATION_NAMES.get(STATIONS["home"]["primary"], "home")
    if divvy.home_primary and divvy.home_primary.is_active:
        hp = divvy.home_primary
        lines.append(f"\n{home_name} (home):")
        lines.append(f"   {hp.ebikes} ebikes \u2022 {hp.scooters} scooters \u2022 {hp.classic_bikes} classic")
    else:
        lines.append(f"\n{home_name}: unavailable")

    for label, key_attr in [("Optiver", "optiver_dropoff"), ("Adyen", "adyen_dropoff")]:
        station: StationAvailability | None = getattr(divvy, key_attr, None)
        if station and station.is_active:
            station_name = STATION_NAMES.get(station.station_id, label)
            lines.append(f"\n{station_name} ({label}):")
            lines.append(f"   {station.docks_available} empty docks")
        else:
            lines.append(f"\n{label}: unavailable")

    return "\n".join(lines)


def build_on_demand_weather_message(weather: WeatherData | None) -> str:
    """Build a shorter message for on-demand weather check."""
    if weather is None:
        return "\u26a0\ufe0f Couldn't fetch weather data right now. Try again in a minute."

    now_str = datetime.now(ZoneInfo(BRIEFING_TIMEZONE)).strftime("%I:%M %p")
    lines = [f"\U0001f321 Weather ({now_str} CT)"]
    lines.append("")
    lines.append(_format_weather_section(weather))
    lines.append("")
    lines.append(f"\U0001f454 {get_clothing_suggestion(weather)}")
    return "\n".join(lines)
