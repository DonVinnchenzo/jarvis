# SPEC-002: Morning Briefing -- Implementation Plan

**Spec:** `specs/002-morning-briefing.md` (Approved)
**Date:** 2026-06-09
**Author:** Claude Code

---

This plan is designed so that a fresh Claude Code session can pick up at any step and know exactly what to do. Each step ends with a working, testable state and a git commit.

---

## Step 0: Prerequisites

One-time setup before writing any code.

### 0.1 Add httpx to production dependencies

The briefing module calls external APIs (Open-Meteo, Divvy GBFS) using `httpx.AsyncClient`. httpx is already in dev dependencies but needs to be in production deps.

Edit `backend/pyproject.toml`:

```toml
dependencies = [
    # ... existing deps ...
    "httpx>=0.27.0",
]
```

Install:

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
pip install -e ".[dev]"
```

### 0.2 Verify external APIs are reachable

```bash
# Open-Meteo (weather)
curl -s "https://api.open-meteo.com/v1/forecast?latitude=41.8967&longitude=-87.6355&current=temperature_2m&temperature_unit=fahrenheit&timezone=America/Chicago" | python3 -m json.tool | head -20

# Divvy station_status
curl -s "https://gbfs.lyft.com/gbfs/2.3/chi/en/station_status.json" | python3 -m json.tool | head -20

# Divvy free_bike_status
curl -s "https://gbfs.lyft.com/gbfs/2.3/chi/en/free_bike_status.json" | python3 -m json.tool | head -20
```

All three should return valid JSON. No API keys needed.

### Verification

- [ ] `python -c "import httpx; print(httpx.__version__)"` works
- [ ] All three external API URLs return JSON

**No git commit for Step 0** -- dependency installation only.

---

## Step 1: Constants + Config

Create the constants module with all hardcoded values for v1. This is the single source of truth for station IDs, coordinates, API URLs, and clothing thresholds.

### Files to create

#### `backend/src/briefing/__init__.py`

Empty file. Makes `briefing` a Python package.

#### `backend/src/briefing/constants.py`

All configuration for the morning briefing module. Hardcoded for v1 per spec.

```python
"""Morning Briefing constants — all hardcoded for v1.

Station IDs sourced from Divvy GBFS station_information.json.
Coordinates for 228 W Hill St, Chicago, IL 60610.
"""

# --- Timezone ---
BRIEFING_TIMEZONE = "America/Chicago"

# --- Coordinates (home address) ---
HOME_LATITUDE = 41.8967
HOME_LONGITUDE = -87.6355

# --- Open-Meteo API ---
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_PARAMS = {
    "latitude": HOME_LATITUDE,
    "longitude": HOME_LONGITUDE,
    "current": ",".join([
        "temperature_2m",
        "apparent_temperature",
        "precipitation",
        "wind_speed_10m",
        "wind_gusts_10m",
        "weather_code",
        "relative_humidity_2m",
    ]),
    "daily": ",".join([
        "temperature_2m_max",
        "temperature_2m_min",
        "apparent_temperature_max",
        "apparent_temperature_min",
        "precipitation_probability_max",
        "wind_speed_10m_max",
        "weather_code",
    ]),
    "temperature_unit": "fahrenheit",
    "wind_speed_unit": "mph",
    "precipitation_unit": "inch",
    "timezone": BRIEFING_TIMEZONE,
    "forecast_days": 1,
}

# --- Divvy GBFS v2.3 ---
GBFS_BASE_URL = "https://gbfs.lyft.com/gbfs/2.3/chi/en"
STATION_STATUS_URL = f"{GBFS_BASE_URL}/station_status.json"
FREE_BIKE_STATUS_URL = f"{GBFS_BASE_URL}/free_bike_status.json"

# --- Station IDs ---
STATIONS = {
    "home": {
        "primary": "a3a40088-a135-11e9-9cda-0a87ae2ba916",   # Franklin & Chicago
        "backup": "a3b35e21-a135-11e9-9cda-0a87ae2ba916",    # Orleans & Chestnut
    },
    "optiver": {
        "dropoff": "2178904806732191280",   # Riverside Plaza & Adams
    },
    "adyen": {
        "dropoff": "2161159315996441640",   # Kingsbury & Kinzie 2
    },
}

STATION_NAMES = {
    "a3a40088-a135-11e9-9cda-0a87ae2ba916": "Franklin & Chicago",
    "a3b35e21-a135-11e9-9cda-0a87ae2ba916": "Orleans & Chestnut",
    "2178904806732191280": "Riverside Plaza & Adams",
    "2161159315996441640": "Kingsbury & Kinzie 2",
}

# --- Per-user office mapping ---
# Maps Telegram user ID (str) to the office station key
USER_OFFICE_STATION: dict[str, dict[str, str]] = {
    # Populated at runtime from settings.user_names_dict keys
    # Format: { "<telegram_id>": { "key": "optiver"|"adyen", "label": "Optiver"|"Adyen" } }
}

# Default mapping (Vincent=Optiver, Christianne=Adyen)
# This is resolved at message-build time using the user's name from settings
OFFICE_BY_NAME = {
    "Vincent": {"key": "optiver", "station_id": "2178904806732191280", "label": "Optiver"},
    "Christianne": {"key": "adyen", "station_id": "2161159315996441640", "label": "Adyen"},
}

# --- Clothing thresholds (feels-like temperature, Fahrenheit) ---
CLOTHING_THRESHOLDS = [
    (80, "Light and breathable — shorts and t-shirt. Stay hydrated."),
    (60, "Perfect biking weather — light layers."),
    (40, "Bring a jacket. Consider gloves for the wind."),
    (25, "Bundle up — warm jacket, gloves, hat. Cover your ears."),
]
CLOTHING_BRUTAL = "It's brutal out there. Full winter gear or consider transit."
CLOTHING_RAIN = "Rain expected — bring a rain jacket and fenders help."
CLOTHING_WIND = "Windy — expect resistance on the ride."

# --- Biking recommendation thresholds ---
BIKE_MIN_FEELS_LIKE = 25   # Fahrenheit
BIKE_MAX_FEELS_LIKE = 100  # Fahrenheit
BIKE_MAX_WIND_SPEED = 20   # mph

# --- HTTP timeout ---
API_TIMEOUT_SECONDS = 10

# --- WMO weather codes to human-readable descriptions ---
# https://open-meteo.com/en/docs (WMO Weather interpretation codes)
WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Weather codes that indicate active precipitation
PRECIPITATION_WEATHER_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99}

# --- Nearby free-floating bike search radius (meters) ---
FREE_BIKE_SEARCH_RADIUS_M = 500
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
python -c "from src.briefing.constants import STATIONS, WEATHER_PARAMS; print('OK:', list(STATIONS.keys()))"
```

Should print: `OK: ['home', 'optiver', 'adyen']`

### Git commit

```
feat(briefing): constants module with station IDs, API URLs, and thresholds

- All Divvy station IDs for home, Optiver, and Adyen
- Open-Meteo API URL and query parameters
- Clothing thresholds and biking recommendation limits
- WMO weather code lookup table
- httpx added to production dependencies
```

---

## Step 2: Weather Fetcher

Async function that calls the Open-Meteo API and returns structured weather data.

### Files to create

#### `backend/src/briefing/weather.py`

```python
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
    temperature: float          # Fahrenheit
    feels_like: float           # Fahrenheit
    precipitation: float        # inches
    wind_speed: float           # mph
    wind_gusts: float           # mph
    humidity: int               # percent
    weather_code: int           # WMO code
    weather_description: str    # Human-readable from WMO code

    # Daily forecast
    high: float                 # Fahrenheit
    low: float                  # Fahrenheit
    feels_like_high: float      # Fahrenheit
    feels_like_low: float       # Fahrenheit
    precip_probability: int     # percent (0-100)
    daily_max_wind: float       # mph
    daily_weather_code: int     # WMO code


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
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
python -c "
import asyncio
from src.briefing.weather import fetch_weather
w = asyncio.run(fetch_weather())
if w:
    print(f'Temperature: {w.temperature}F, Feels like: {w.feels_like}F')
    print(f'High: {w.high}F, Low: {w.low}F')
    print(f'Wind: {w.wind_speed} mph, Precip prob: {w.precip_probability}%')
    print(f'Description: {w.weather_description}')
else:
    print('FAILED to fetch weather')
"
```

Should print live weather data for Chicago.

### Git commit

```
feat(briefing): weather fetcher with Open-Meteo API integration

- WeatherData dataclass with current + daily forecast fields
- fetch_weather() async function with 10s httpx timeout
- Returns None on any failure (timeout, HTTP error, bad data)
- WMO weather code to human-readable description mapping
```

---

## Step 3: Divvy Fetcher

Async functions that call the Divvy GBFS API for station status and free-floating bikes.

### Files to create

#### `backend/src/briefing/divvy.py`

```python
"""Fetch Divvy bike-share availability from GBFS API."""

import logging
import math
from dataclasses import dataclass, field

import httpx

from src.briefing.constants import (
    API_TIMEOUT_SECONDS,
    FREE_BIKE_SEARCH_RADIUS_M,
    FREE_BIKE_STATUS_URL,
    HOME_LATITUDE,
    HOME_LONGITUDE,
    STATION_STATUS_URL,
    STATIONS,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StationAvailability:
    """Availability data for a single Divvy station."""

    station_id: str
    classic_bikes: int = 0
    ebikes: int = 0
    scooters: int = 0
    docks_available: int = 0
    is_installed: bool = True
    is_renting: bool = True
    is_returning: bool = True

    @property
    def total_vehicles(self) -> int:
        return self.classic_bikes + self.ebikes + self.scooters

    @property
    def is_active(self) -> bool:
        return self.is_installed and self.is_renting


@dataclass(frozen=True)
class NearbyFreeBikes:
    """Free-floating vehicles near the home station."""

    ebikes: int = 0
    scooters: int = 0


@dataclass
class DivvyData:
    """All Divvy data needed for the morning briefing."""

    home_primary: StationAvailability | None = None
    home_backup: StationAvailability | None = None
    optiver_dropoff: StationAvailability | None = None
    adyen_dropoff: StationAvailability | None = None
    nearby_free: NearbyFreeBikes = field(default_factory=NearbyFreeBikes)


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two lat/lon points in meters."""
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_station(raw: dict) -> StationAvailability:
    """Parse a single station from the GBFS station_status response."""
    # Count vehicle types from vehicle_types_available (GBFS v2.3)
    classic = 0
    ebikes = 0
    scooters = 0
    for vt in raw.get("vehicle_types_available", []):
        vt_id = vt.get("vehicle_type_id", "")
        count = vt.get("count", 0)
        if "scooter" in vt_id.lower():
            scooters += count
        elif "electric" in vt_id.lower() or "ebike" in vt_id.lower():
            ebikes += count
        elif "classic" in vt_id.lower() or "bike" in vt_id.lower():
            classic += count

    # Fallback: if no vehicle_types_available, use num_bikes_available
    if classic == 0 and ebikes == 0 and scooters == 0:
        classic = raw.get("num_bikes_available", 0)

    return StationAvailability(
        station_id=raw.get("station_id", ""),
        classic_bikes=classic,
        ebikes=ebikes,
        scooters=scooters,
        docks_available=raw.get("num_docks_available", 0),
        is_installed=bool(raw.get("is_installed", 1)),
        is_renting=bool(raw.get("is_renting", 1)),
        is_returning=bool(raw.get("is_returning", 1)),
    )


async def fetch_station_status() -> dict[str, StationAvailability] | None:
    """Fetch station status from Divvy GBFS. Returns dict of station_id -> availability.

    Only returns data for stations we track (defined in STATIONS).
    Returns None on failure.
    """
    tracked_ids: set[str] = set()
    for group in STATIONS.values():
        for sid in group.values():
            tracked_ids.add(sid)

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
            resp = await client.get(STATION_STATUS_URL)
            resp.raise_for_status()
            data = resp.json()

        stations_raw = data.get("data", {}).get("stations", [])
        result: dict[str, StationAvailability] = {}

        for raw in stations_raw:
            sid = raw.get("station_id", "")
            if sid in tracked_ids:
                result[sid] = _parse_station(raw)

        return result

    except httpx.TimeoutException:
        logger.error("Divvy station_status API timed out after %ds", API_TIMEOUT_SECONDS)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Divvy station_status returned HTTP %d", e.response.status_code)
        return None
    except Exception:
        logger.exception("Unexpected error fetching Divvy station status")
        return None


async def fetch_free_bikes() -> NearbyFreeBikes | None:
    """Fetch free-floating bikes/scooters near the home station.

    Filters to vehicles within FREE_BIKE_SEARCH_RADIUS_M of home.
    Returns None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
            resp = await client.get(FREE_BIKE_STATUS_URL)
            resp.raise_for_status()
            data = resp.json()

        bikes_raw = data.get("data", {}).get("bikes", [])
        ebikes = 0
        scooters = 0

        for bike in bikes_raw:
            lat = bike.get("lat")
            lon = bike.get("lon")
            if lat is None or lon is None:
                continue

            distance = _haversine_meters(HOME_LATITUDE, HOME_LONGITUDE, lat, lon)
            if distance > FREE_BIKE_SEARCH_RADIUS_M:
                continue

            vehicle_type = bike.get("vehicle_type_id", "")
            if "scooter" in vehicle_type.lower():
                scooters += 1
            else:
                ebikes += 1

        return NearbyFreeBikes(ebikes=ebikes, scooters=scooters)

    except httpx.TimeoutException:
        logger.error("Divvy free_bike_status API timed out after %ds", API_TIMEOUT_SECONDS)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Divvy free_bike_status returned HTTP %d", e.response.status_code)
        return None
    except Exception:
        logger.exception("Unexpected error fetching Divvy free bikes")
        return None


def build_divvy_data(
    station_status: dict[str, StationAvailability] | None,
    free_bikes: NearbyFreeBikes | None,
) -> DivvyData:
    """Assemble DivvyData from raw API results. Handles partial failures."""
    divvy = DivvyData()

    if station_status:
        home_primary_id = STATIONS["home"]["primary"]
        home_backup_id = STATIONS["home"]["backup"]
        optiver_id = STATIONS["optiver"]["dropoff"]
        adyen_id = STATIONS["adyen"]["dropoff"]

        divvy.home_primary = station_status.get(home_primary_id)
        divvy.home_backup = station_status.get(home_backup_id)
        divvy.optiver_dropoff = station_status.get(optiver_id)
        divvy.adyen_dropoff = station_status.get(adyen_id)

    if free_bikes:
        divvy.nearby_free = free_bikes

    return divvy
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
python -c "
import asyncio
from src.briefing.divvy import fetch_station_status, fetch_free_bikes, build_divvy_data

async def main():
    ss = await fetch_station_status()
    fb = await fetch_free_bikes()
    d = build_divvy_data(ss, fb)
    if d.home_primary:
        hp = d.home_primary
        print(f'Home (Franklin & Chicago): {hp.ebikes} ebikes, {hp.scooters} scooters, {hp.classic_bikes} classic')
        print(f'  Active: {hp.is_active}, Docks: {hp.docks_available}')
    else:
        print('Home station: unavailable')
    if d.optiver_dropoff:
        print(f'Optiver docks available: {d.optiver_dropoff.docks_available}')
    print(f'Nearby free-floating: {d.nearby_free.ebikes} ebikes, {d.nearby_free.scooters} scooters')

asyncio.run(main())
"
```

Should print live Divvy data for all tracked stations.

### Git commit

```
feat(briefing): Divvy fetcher with station status and free-floating bikes

- StationAvailability dataclass with vehicle breakdown (classic/ebike/scooter)
- fetch_station_status() filters to tracked stations only
- fetch_free_bikes() finds free-floating vehicles within 500m of home
- build_divvy_data() assembles DivvyData from raw results
- Haversine distance calculation for nearby bike search
- Handles is_installed/is_renting/is_returning per spec
- Returns None on any failure (timeout, HTTP error, bad data)
```

---

## Step 4: Clothing Logic + Biking Recommendation

Pure functions with no external dependencies. Easy to test in isolation.

### Files to create

#### `backend/src/briefing/clothing.py`

```python
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

    # Rain modifier: current precipitation OR high probability
    has_rain = (
        weather.precipitation > 0
        or weather.precip_probability > 60
        or weather.weather_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
    )
    if has_rain:
        parts.append(CLOTHING_RAIN)

    # Wind modifier
    if weather.wind_speed > 15:
        parts.append(CLOTHING_WIND)

    return "\n".join(parts)
```

#### `backend/src/briefing/recommendation.py`

```python
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
        return False, "Data unavailable -- check manually."

    reasons_no: list[str] = []

    # --- Weather checks ---
    if weather is not None:
        # Rain check
        is_raining = (
            weather.precipitation > 0
            or weather.weather_code in PRECIPITATION_WEATHER_CODES
        )
        rain_likely = weather.precip_probability > 60

        if is_raining:
            reasons_no.append("rain expected all morning")
        elif rain_likely:
            reasons_no.append(f"{weather.precip_probability}% chance of rain")

        # Temperature check
        if weather.feels_like < BIKE_MIN_FEELS_LIKE:
            reasons_no.append(f"feels like {weather.feels_like:.0f}\u00b0F -- dangerously cold")
        elif weather.feels_like > BIKE_MAX_FEELS_LIKE:
            reasons_no.append(f"feels like {weather.feels_like:.0f}\u00b0F -- dangerously hot")

        # Wind check
        if weather.wind_speed >= BIKE_MAX_WIND_SPEED:
            reasons_no.append(f"wind at {weather.wind_speed:.0f} mph")

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
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
python -c "
from src.briefing.weather import WeatherData
from src.briefing.clothing import get_clothing_suggestion

# Test warm weather
w = WeatherData(temperature=75, feels_like=78, precipitation=0, wind_speed=8,
    wind_gusts=12, humidity=45, weather_code=2, weather_description='Partly cloudy',
    high=82, low=65, feels_like_high=84, feels_like_low=63, precip_probability=10,
    daily_max_wind=12, daily_weather_code=2)
print('Warm:', get_clothing_suggestion(w))
print()

# Test cold + rainy
w2 = WeatherData(temperature=38, feels_like=30, precipitation=0.1, wind_speed=18,
    wind_gusts=25, humidity=80, weather_code=61, weather_description='Rain',
    high=42, low=35, feels_like_high=36, feels_like_low=28, precip_probability=90,
    daily_max_wind=22, daily_weather_code=63)
print('Cold+Rain:', get_clothing_suggestion(w2))
"
```

### Git commit

```
feat(briefing): clothing logic and biking recommendation

- get_clothing_suggestion(): pure function, temperature + rain + wind
- get_bike_recommendation(): returns (bool, reason) tuple
- Checks feels-like temp, precipitation, wind speed, bike availability
- Falls back to backup station + free-floating when home is empty
```

---

## Step 5: Message Builder

Builds per-user Telegram messages. This is the formatting layer that ties weather, Divvy, clothing, and recommendation together.

### Files to create

#### `backend/src/briefing/message_builder.py`

```python
"""Build morning briefing Telegram messages."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.briefing.clothing import get_clothing_suggestion
from src.briefing.constants import (
    BRIEFING_TIMEZONE,
    OFFICE_BY_NAME,
    STATION_NAMES,
    STATIONS,
    WMO_WEATHER_CODES,
)
from src.briefing.divvy import DivvyData, StationAvailability
from src.briefing.recommendation import get_bike_recommendation
from src.briefing.weather import WeatherData

logger = logging.getLogger(__name__)

# Weather code to emoji mapping (simplified)
_WEATHER_EMOJIS = {
    0: "\u2600\ufe0f",      # Clear sky -> sun
    1: "\U0001f324\ufe0f",  # Mainly clear
    2: "\u26c5",             # Partly cloudy
    3: "\u2601\ufe0f",      # Overcast
    45: "\U0001f32b\ufe0f", # Fog
    48: "\U0001f32b\ufe0f", # Rime fog
}
# Rain/snow/storm codes all map to rain emoji
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
    emoji_line = (
        f"\U0001f321 Weather: {weather.temperature:.0f}\u00b0F "
        f"(feels like {weather.feels_like:.0f}\u00b0F)"
    )
    range_line = f"\u2191 High {weather.high:.0f}\u00b0F / \u2193 Low {weather.low:.0f}\u00b0F"
    detail_line = (
        f"{description} \u2022 {weather.precip_probability}% chance of rain "
        f"\u2022 Wind {weather.wind_speed:.0f} mph"
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
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
python -c "
from src.briefing.weather import WeatherData
from src.briefing.divvy import DivvyData, StationAvailability, NearbyFreeBikes
from src.briefing.message_builder import build_briefing_message

# Sunny day, bikes available
weather = WeatherData(
    temperature=72, feels_like=75, precipitation=0, wind_speed=8,
    wind_gusts=12, humidity=45, weather_code=2, weather_description='Partly cloudy',
    high=82, low=65, feels_like_high=84, feels_like_low=63, precip_probability=10,
    daily_max_wind=12, daily_weather_code=2,
)
divvy = DivvyData(
    home_primary=StationAvailability('home', classic_bikes=5, ebikes=3, scooters=2, docks_available=8),
    optiver_dropoff=StationAvailability('opt', docks_available=14),
    adyen_dropoff=StationAvailability('adn', docks_available=17),
    nearby_free=NearbyFreeBikes(),
)

print('=== Vincent ===')
print(build_briefing_message('Vincent', weather, divvy))
print()
print('=== Christianne ===')
print(build_briefing_message('Christianne', weather, divvy))
print()

# Partial failure: no weather
print('=== No weather ===')
print(build_briefing_message('Vincent', None, divvy))
"
```

### Git commit

```
feat(briefing): message builder with per-user personalization

- build_briefing_message(): full morning briefing with weather, bikes, clothing, recommendation
- Vincent sees Optiver docks, Christianne sees Adyen docks
- Handles partial failure: weather down, Divvy down, both down
- Backup station note when home has no ebikes/scooters
- build_on_demand_bikes_message(): short format for "any bikes?" queries
- build_on_demand_weather_message(): short format for weather queries
- Cross-module hook: todays_events parameter for Social Circle integration
```

---

## Step 6: Briefing Engine

Orchestrates the full briefing flow. Parallel fetch, build messages, send to users. Follows the `ReminderEngine` pattern from `backend/src/engine/reminder_engine.py`.

### Files to create

#### `backend/src/briefing/engine.py`

```python
"""Morning Briefing engine — orchestrates fetch, build, and send."""

import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.briefing.constants import BRIEFING_TIMEZONE
from src.briefing.divvy import DivvyData, build_divvy_data, fetch_free_bikes, fetch_station_status
from src.briefing.message_builder import (
    build_briefing_message,
    build_on_demand_bikes_message,
    build_on_demand_weather_message,
)
from src.briefing.weather import WeatherData, fetch_weather
from src.config import Settings

logger = logging.getLogger(__name__)


async def _fetch_todays_events(db: AsyncSession, tz_name: str) -> list[str]:
    """Cross-module: get Social Circle events happening today.

    Returns a list of human-readable event strings for the briefing.
    If Social Circle module is not available, returns empty list.
    """
    try:
        from src.engine.reminder_engine import ReminderEngine
        from src.models.event import ContactEvent
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        tz = ZoneInfo(tz_name)
        today = datetime.now(tz).date()

        stmt = (
            select(ContactEvent)
            .where(ContactEvent.recurring.is_(True))
            .options(
                selectinload(ContactEvent.contact),
                selectinload(ContactEvent.child),
            )
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        today_events: list[str] = []
        for event in events:
            occ = ReminderEngine._make_occurrence_date(event.month, event.day, today.year)
            if occ is None:
                continue
            if occ != today:
                continue

            contact_name = event.contact.name if event.contact else "Someone"
            if event.event_type == "birthday":
                age_str = ""
                if event.year is not None:
                    age = today.year - event.year
                    age_str = f" (turns {age})"
                today_events.append(f"\U0001f382 {contact_name}'s birthday{age_str}")
            elif event.event_type == "anniversary":
                label = event.label or f"{contact_name}'s anniversary"
                today_events.append(f"\U0001f48d {label}")
            elif event.event_type == "child_birthday":
                child_name = event.child.name if event.child else "Child"
                age_str = ""
                if event.year is not None:
                    age = today.year - event.year
                    age_str = f" (turns {age})"
                today_events.append(f"\U0001f388 {child_name} ({contact_name}'s child) birthday{age_str}")
            elif event.event_type == "custom":
                label = event.label or f"{contact_name}'s event"
                today_events.append(f"\U0001f4c5 {label}")

        return today_events

    except Exception:
        logger.debug("Could not fetch Social Circle events (module may not be ready)", exc_info=True)
        return []


class BriefingEngine:
    """Orchestrates the morning briefing: fetch data, build messages, send."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def run(self) -> dict:
        """Run the full morning briefing for all users.

        Fetches weather and Divvy data in parallel, builds per-user messages,
        sends via Telegram. Returns a summary dict.
        """
        # Skip on weekends
        tz = ZoneInfo(BRIEFING_TIMEZONE)
        now = datetime.now(tz)
        if now.weekday() in (5, 6):  # Saturday=5, Sunday=6
            logger.info("Skipping morning briefing on weekend (%s)", now.strftime("%A"))
            return {"status": "skipped", "reason": "weekend"}

        # Parallel fetch: weather, station_status, free_bikes
        weather_result, station_result, free_bikes_result = await asyncio.gather(
            fetch_weather(),
            fetch_station_status(),
            fetch_free_bikes(),
            return_exceptions=True,
        )

        # Unwrap results (gather with return_exceptions=True returns exceptions as values)
        weather: WeatherData | None = None
        if isinstance(weather_result, WeatherData):
            weather = weather_result
        elif isinstance(weather_result, Exception):
            logger.error("Weather fetch raised exception: %s", weather_result)

        station_status = None
        if isinstance(station_result, dict):
            station_status = station_result
        elif isinstance(station_result, Exception):
            logger.error("Station status fetch raised exception: %s", station_result)

        free_bikes = None
        if not isinstance(free_bikes_result, Exception):
            free_bikes = free_bikes_result
        else:
            logger.error("Free bikes fetch raised exception: %s", free_bikes_result)

        # Build DivvyData from raw results
        divvy = build_divvy_data(station_status, free_bikes)

        # Cross-module: get today's Social Circle events
        todays_events = await _fetch_todays_events(self.db, self.settings.TIMEZONE)

        # Build and send per-user messages
        from src.engine.telegram_sender import send_to_user

        user_names = self.settings.user_names_dict
        sent_count = 0
        errors: list[str] = []

        for user_id_str, user_name in user_names.items():
            user_id = int(user_id_str)
            message = build_briefing_message(user_name, weather, divvy, todays_events)

            try:
                await send_to_user(message, user_id, self.settings)
                sent_count += 1
                logger.info("Sent morning briefing to %s (%s)", user_name, user_id)
            except Exception as e:
                logger.exception("Failed to send briefing to %s", user_name)
                errors.append(f"Send failed for {user_name}: {e}")

        status = "completed" if not errors else "completed_with_errors"
        return {
            "status": status,
            "sent": sent_count,
            "weather_available": weather is not None,
            "divvy_available": station_status is not None,
            "todays_events": len(todays_events),
            "errors": errors,
        }

    async def get_briefing_for_user(self, user_name: str) -> str:
        """Generate an on-demand briefing for a single user (not sent, just returned)."""
        weather_result, station_result, free_bikes_result = await asyncio.gather(
            fetch_weather(),
            fetch_station_status(),
            fetch_free_bikes(),
            return_exceptions=True,
        )

        weather = weather_result if isinstance(weather_result, WeatherData) else None
        station_status = station_result if isinstance(station_result, dict) else None
        free_bikes = free_bikes_result if not isinstance(free_bikes_result, Exception) else None

        divvy = build_divvy_data(station_status, free_bikes)
        todays_events = await _fetch_todays_events(self.db, self.settings.TIMEZONE)

        return build_briefing_message(user_name, weather, divvy, todays_events)

    @staticmethod
    async def get_bikes_status() -> str:
        """Get current Divvy status for all tracked stations (on-demand)."""
        station_result, free_bikes_result = await asyncio.gather(
            fetch_station_status(),
            fetch_free_bikes(),
            return_exceptions=True,
        )

        station_status = station_result if isinstance(station_result, dict) else None
        free_bikes = free_bikes_result if not isinstance(free_bikes_result, Exception) else None
        divvy = build_divvy_data(station_status, free_bikes)

        return build_on_demand_bikes_message(divvy)

    @staticmethod
    async def get_weather_status() -> str:
        """Get current weather (on-demand)."""
        weather = await fetch_weather()
        return build_on_demand_weather_message(weather)
```

### Files to modify

#### `backend/src/engine/telegram_sender.py` -- Add `send_to_user` function

Add a new function below the existing `send_to_all_users` for sending to a single user (the briefing needs per-user messages since each message is personalized):

```python
async def send_to_user(message: str, user_id: int, settings: Settings) -> int | None:
    """Send message to a single Telegram user. Returns message_id or None."""
    from telegram import Bot

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured, skipping send")
        return None

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        result = await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=None,  # No markdown -- briefing uses emojis, not markdown formatting
        )
        logger.info("Sent message to user %s (message_id=%s)", user_id, result.message_id)
        return result.message_id
    except Exception:
        logger.exception("Failed to send to user %s", user_id)
        raise
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
python -c "
import asyncio
from src.briefing.engine import BriefingEngine

async def main():
    # Test static methods (no DB or settings needed)
    bikes_msg = await BriefingEngine.get_bikes_status()
    print('=== BIKES STATUS ===')
    print(bikes_msg)
    print()
    weather_msg = await BriefingEngine.get_weather_status()
    print('=== WEATHER STATUS ===')
    print(weather_msg)

asyncio.run(main())
"
```

### Git commit

```
feat(briefing): briefing engine with parallel fetch and per-user delivery

- BriefingEngine class following ReminderEngine pattern
- Parallel fetch via asyncio.gather(return_exceptions=True)
- Per-user message building (Vincent/Optiver, Christianne/Adyen)
- Weekend skip logic (Saturday/Sunday)
- Cross-module integration: includes Social Circle events for today
- On-demand methods: get_briefing_for_user, get_bikes_status, get_weather_status
- send_to_user() added to telegram_sender for per-user sends
```

---

## Step 7: Routes

Create the briefing API endpoints and wire them into main.py.

### Files to create

#### `backend/src/briefing/schemas.py`

Pydantic models for request/response validation:

```python
"""Pydantic schemas for the briefing module."""

from pydantic import BaseModel


class BriefingRunResponse(BaseModel):
    status: str
    sent: int = 0
    weather_available: bool = False
    divvy_available: bool = False
    todays_events: int = 0
    errors: list[str] = []
```

#### `backend/src/routes/briefing.py`

Four endpoints per spec:

```python
"""Morning Briefing API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.briefing.engine import BriefingEngine
from src.briefing.schemas import BriefingRunResponse
from src.config import get_settings
from src.database import get_db

router = APIRouter()


@router.post("/briefing/run", response_model=BriefingRunResponse)
async def run_briefing(
    db: AsyncSession = Depends(get_db),
):
    """Trigger morning briefing for all users. Called by cron at 07:00 CT."""
    settings = get_settings()
    engine = BriefingEngine(db, settings)
    result = await engine.run()
    return result


@router.get("/briefing")
async def get_briefing(
    user_name: str = Query(..., description="User display name (Vincent or Christianne)"),
    db: AsyncSession = Depends(get_db),
):
    """Generate on-demand briefing for a specific user. Returns the message text."""
    settings = get_settings()
    engine = BriefingEngine(db, settings)
    message = await engine.get_briefing_for_user(user_name)
    return {"message": message}


@router.get("/briefing/bikes")
async def get_bikes():
    """Get current Divvy status for all tracked stations."""
    message = await BriefingEngine.get_bikes_status()
    return {"message": message}


@router.get("/briefing/weather")
async def get_weather():
    """Get current weather data."""
    message = await BriefingEngine.get_weather_status()
    return {"message": message}
```

### Files to modify

#### `backend/src/main.py` -- Wire the briefing router

Add import and include_router:

```python
from src.routes import briefing, children, contacts, events, health, notes, reminders, search, upcoming

# ... existing routers ...
app.include_router(briefing.router, prefix="/api", tags=["briefing"])
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate
uvicorn src.main:app --host 127.0.0.1 --port 8000 &
sleep 2

API_KEY=$(grep JARVIS_API_KEY /Users/vincent/jarvis/.env | cut -d'=' -f2)

# Test weather endpoint
echo "=== GET /api/briefing/weather ==="
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/briefing/weather | python3 -m json.tool

# Test bikes endpoint
echo "=== GET /api/briefing/bikes ==="
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/api/briefing/bikes | python3 -m json.tool

# Test on-demand briefing for Vincent
echo "=== GET /api/briefing?user_name=Vincent ==="
curl -s -H "X-API-Key: $API_KEY" "http://localhost:8000/api/briefing?user_name=Vincent" | python3 -m json.tool

# Test on-demand briefing for Christianne
echo "=== GET /api/briefing?user_name=Christianne ==="
curl -s -H "X-API-Key: $API_KEY" "http://localhost:8000/api/briefing?user_name=Christianne" | python3 -m json.tool

# Test the run endpoint (will actually send Telegram messages!)
# Only run this if you want real messages sent:
# echo "=== POST /api/briefing/run ==="
# curl -s -X POST -H "X-API-Key: $API_KEY" http://localhost:8000/api/briefing/run | python3 -m json.tool

# Lint
ruff check .

kill %1
```

### Git commit

```
feat(briefing): API routes wired into FastAPI app

- POST /api/briefing/run: trigger morning briefing (cron target)
- GET /api/briefing?user_name=X: on-demand briefing for a user
- GET /api/briefing/bikes: current Divvy status
- GET /api/briefing/weather: current weather
- Briefing router registered in main.py
```

---

## Step 8: Tests

Unit and integration tests for the briefing module. Tests use synthetic data -- no external API calls.

### Files to create

#### `backend/tests/test_clothing.py`

Tests for clothing logic across all temperature ranges and weather conditions:

```python
"""Tests for clothing suggestion logic."""

import pytest

from src.briefing.clothing import get_clothing_suggestion
from src.briefing.weather import WeatherData


def _make_weather(**overrides) -> WeatherData:
    """Factory for WeatherData with sensible defaults."""
    defaults = dict(
        temperature=72, feels_like=72, precipitation=0, wind_speed=8,
        wind_gusts=12, humidity=45, weather_code=2, weather_description="Partly cloudy",
        high=80, low=60, feels_like_high=80, feels_like_low=60,
        precip_probability=10, daily_max_wind=12, daily_weather_code=2,
    )
    defaults.update(overrides)
    return WeatherData(**defaults)


class TestClothingSuggestion:
    def test_hot_weather(self):
        w = _make_weather(feels_like=85)
        result = get_clothing_suggestion(w)
        assert "shorts and t-shirt" in result.lower() or "light and breathable" in result.lower()

    def test_perfect_weather(self):
        w = _make_weather(feels_like=70)
        result = get_clothing_suggestion(w)
        assert "light layers" in result.lower()

    def test_cool_weather(self):
        w = _make_weather(feels_like=50)
        result = get_clothing_suggestion(w)
        assert "jacket" in result.lower()

    def test_cold_weather(self):
        w = _make_weather(feels_like=30)
        result = get_clothing_suggestion(w)
        assert "bundle up" in result.lower() or "warm jacket" in result.lower()

    def test_brutal_cold(self):
        w = _make_weather(feels_like=10)
        result = get_clothing_suggestion(w)
        assert "brutal" in result.lower() or "full winter gear" in result.lower()

    def test_rain_from_precipitation(self):
        w = _make_weather(precipitation=0.2, weather_code=61)
        result = get_clothing_suggestion(w)
        assert "rain jacket" in result.lower()

    def test_rain_from_probability(self):
        w = _make_weather(precip_probability=75)
        result = get_clothing_suggestion(w)
        assert "rain jacket" in result.lower()

    def test_no_rain_at_50_percent(self):
        w = _make_weather(precip_probability=50)
        result = get_clothing_suggestion(w)
        assert "rain jacket" not in result.lower()

    def test_wind_modifier(self):
        w = _make_weather(wind_speed=18)
        result = get_clothing_suggestion(w)
        assert "windy" in result.lower() or "resistance" in result.lower()

    def test_no_wind_at_15(self):
        w = _make_weather(wind_speed=15)
        result = get_clothing_suggestion(w)
        assert "windy" not in result.lower()

    def test_cold_rain_wind_combo(self):
        w = _make_weather(feels_like=35, precipitation=0.1, wind_speed=20, weather_code=63)
        result = get_clothing_suggestion(w)
        assert "jacket" in result.lower()
        assert "rain" in result.lower()
        assert "wind" in result.lower()

    def test_threshold_boundary_80(self):
        w = _make_weather(feels_like=80)
        result = get_clothing_suggestion(w)
        assert "light and breathable" in result.lower() or "shorts" in result.lower()

    def test_threshold_boundary_60(self):
        w = _make_weather(feels_like=60)
        result = get_clothing_suggestion(w)
        assert "light layers" in result.lower()

    def test_threshold_boundary_40(self):
        w = _make_weather(feels_like=40)
        result = get_clothing_suggestion(w)
        assert "jacket" in result.lower()

    def test_threshold_boundary_25(self):
        w = _make_weather(feels_like=25)
        result = get_clothing_suggestion(w)
        assert "bundle up" in result.lower() or "warm jacket" in result.lower()
```

#### `backend/tests/test_recommendation.py`

Tests for biking recommendation logic:

```python
"""Tests for biking recommendation logic."""

import pytest

from src.briefing.divvy import DivvyData, NearbyFreeBikes, StationAvailability
from src.briefing.recommendation import get_bike_recommendation
from src.briefing.weather import WeatherData


def _make_weather(**overrides) -> WeatherData:
    defaults = dict(
        temperature=72, feels_like=72, precipitation=0, wind_speed=8,
        wind_gusts=12, humidity=45, weather_code=2, weather_description="Partly cloudy",
        high=80, low=60, feels_like_high=80, feels_like_low=60,
        precip_probability=10, daily_max_wind=12, daily_weather_code=2,
    )
    defaults.update(overrides)
    return WeatherData(**defaults)


def _make_divvy(**overrides) -> DivvyData:
    defaults = dict(
        home_primary=StationAvailability("home", ebikes=3, scooters=2, classic_bikes=5, docks_available=8),
        optiver_dropoff=StationAvailability("opt", docks_available=14),
        adyen_dropoff=StationAvailability("adn", docks_available=17),
        nearby_free=NearbyFreeBikes(),
    )
    defaults.update(overrides)
    return DivvyData(**defaults)


class TestBikeRecommendation:
    def test_perfect_conditions(self):
        should, reason = get_bike_recommendation(_make_weather(), _make_divvy())
        assert should is True
        assert "great conditions" in reason

    def test_rain_current(self):
        w = _make_weather(precipitation=0.1, weather_code=61)
        should, reason = get_bike_recommendation(w, _make_divvy())
        assert should is False
        assert "rain" in reason

    def test_rain_high_probability(self):
        w = _make_weather(precip_probability=85)
        should, reason = get_bike_recommendation(w, _make_divvy())
        assert should is False
        assert "rain" in reason.lower() or "%" in reason

    def test_too_cold(self):
        w = _make_weather(feels_like=20)
        should, reason = get_bike_recommendation(w, _make_divvy())
        assert should is False
        assert "cold" in reason

    def test_too_hot(self):
        w = _make_weather(feels_like=105)
        should, reason = get_bike_recommendation(w, _make_divvy())
        assert should is False
        assert "hot" in reason

    def test_too_windy(self):
        w = _make_weather(wind_speed=20)
        should, reason = get_bike_recommendation(w, _make_divvy())
        assert should is False
        assert "wind" in reason

    def test_wind_at_19_ok(self):
        w = _make_weather(wind_speed=19)
        should, _ = get_bike_recommendation(w, _make_divvy())
        assert should is True

    def test_no_bikes_no_backup(self):
        d = _make_divvy(
            home_primary=StationAvailability("home", ebikes=0, scooters=0, classic_bikes=0),
            home_backup=StationAvailability("backup", ebikes=0, scooters=0, classic_bikes=0),
            nearby_free=NearbyFreeBikes(ebikes=0, scooters=0),
        )
        should, reason = get_bike_recommendation(_make_weather(), d)
        assert should is False
        assert "no bikes" in reason

    def test_no_bikes_but_backup_has(self):
        d = _make_divvy(
            home_primary=StationAvailability("home", ebikes=0, scooters=0, classic_bikes=0),
            home_backup=StationAvailability("backup", ebikes=2, scooters=0, classic_bikes=0),
        )
        should, _ = get_bike_recommendation(_make_weather(), d)
        assert should is True

    def test_no_bikes_but_free_floating(self):
        d = _make_divvy(
            home_primary=StationAvailability("home", ebikes=0, scooters=0, classic_bikes=0),
            home_backup=StationAvailability("backup", ebikes=0, scooters=0, classic_bikes=0),
            nearby_free=NearbyFreeBikes(ebikes=1, scooters=0),
        )
        should, _ = get_bike_recommendation(_make_weather(), d)
        assert should is True

    def test_station_not_installed(self):
        d = _make_divvy(
            home_primary=StationAvailability("home", is_installed=False),
        )
        should, reason = get_bike_recommendation(_make_weather(), d)
        assert should is False
        assert "unavailable" in reason

    def test_both_apis_down(self):
        should, reason = get_bike_recommendation(None, None)
        assert should is False
        assert "unavailable" in reason.lower() or "check manually" in reason.lower()

    def test_weather_down_bikes_ok(self):
        should, _ = get_bike_recommendation(None, _make_divvy())
        # Weather unknown, bikes available -- should still recommend
        assert should is True

    def test_divvy_down_weather_ok(self):
        should, _ = get_bike_recommendation(_make_weather(), None)
        # Weather fine, bikes unknown -- should still recommend (can't check bikes)
        assert should is True

    def test_multiple_negative_factors(self):
        w = _make_weather(feels_like=20, wind_speed=25)
        should, reason = get_bike_recommendation(w, _make_divvy())
        assert should is False
        assert "cold" in reason and "wind" in reason
```

#### `backend/tests/test_message_builder.py`

Tests for message formatting:

```python
"""Tests for briefing message builder."""

import pytest

from src.briefing.divvy import DivvyData, NearbyFreeBikes, StationAvailability
from src.briefing.message_builder import (
    build_briefing_message,
    build_on_demand_bikes_message,
    build_on_demand_weather_message,
)
from src.briefing.weather import WeatherData


def _make_weather(**overrides) -> WeatherData:
    defaults = dict(
        temperature=72, feels_like=75, precipitation=0, wind_speed=8,
        wind_gusts=12, humidity=45, weather_code=2, weather_description="Partly cloudy",
        high=82, low=65, feels_like_high=84, feels_like_low=63,
        precip_probability=10, daily_max_wind=12, daily_weather_code=2,
    )
    defaults.update(overrides)
    return WeatherData(**defaults)


def _make_divvy(**overrides) -> DivvyData:
    defaults = dict(
        home_primary=StationAvailability("home", classic_bikes=5, ebikes=3, scooters=2, docks_available=8),
        optiver_dropoff=StationAvailability("opt", docks_available=14),
        adyen_dropoff=StationAvailability("adn", docks_available=17),
        nearby_free=NearbyFreeBikes(),
    )
    defaults.update(overrides)
    return DivvyData(**defaults)


class TestBriefingMessage:
    def test_vincent_sees_optiver(self):
        msg = build_briefing_message("Vincent", _make_weather(), _make_divvy())
        assert "Optiver" in msg
        assert "Adyen" not in msg
        assert "Good morning Vincent" in msg

    def test_christianne_sees_adyen(self):
        msg = build_briefing_message("Christianne", _make_weather(), _make_divvy())
        assert "Adyen" in msg
        assert "Optiver" not in msg
        assert "Good morning Christianne" in msg

    def test_weather_section_included(self):
        msg = build_briefing_message("Vincent", _make_weather(), _make_divvy())
        assert "72\u00b0F" in msg
        assert "feels like 75\u00b0F" in msg
        assert "High 82\u00b0F" in msg
        assert "Low 65\u00b0F" in msg
        assert "10% chance of rain" in msg

    def test_bikes_section_included(self):
        msg = build_briefing_message("Vincent", _make_weather(), _make_divvy())
        assert "3 ebikes" in msg
        assert "2 scooters" in msg
        assert "5 classic bikes" in msg

    def test_docks_section_included(self):
        msg = build_briefing_message("Vincent", _make_weather(), _make_divvy())
        assert "14 empty docks" in msg
        assert "plenty of room" in msg

    def test_recommendation_included(self):
        msg = build_briefing_message("Vincent", _make_weather(), _make_divvy())
        assert "Bike today?" in msg
        assert "Yes" in msg

    def test_weather_unavailable(self):
        msg = build_briefing_message("Vincent", None, _make_divvy())
        assert "Weather data unavailable" in msg
        assert "3 ebikes" in msg  # Divvy still present

    def test_divvy_unavailable(self):
        msg = build_briefing_message("Vincent", _make_weather(), None)
        assert "72\u00b0F" in msg  # Weather still present
        assert "Bike data unavailable" in msg

    def test_both_unavailable(self):
        msg = build_briefing_message("Vincent", None, None)
        assert "Good morning Vincent" in msg
        assert "Weather data unavailable" in msg
        assert "Bike data unavailable" in msg

    def test_station_not_installed(self):
        d = _make_divvy(
            home_primary=StationAvailability("home", is_installed=False),
        )
        msg = build_briefing_message("Vincent", _make_weather(), d)
        assert "temporarily unavailable" in msg

    def test_docks_full(self):
        d = _make_divvy(
            optiver_dropoff=StationAvailability("opt", docks_available=0),
        )
        msg = build_briefing_message("Vincent", _make_weather(), d)
        assert "FULL" in msg or "no empty docks" in msg

    def test_docks_almost_full(self):
        d = _make_divvy(
            optiver_dropoff=StationAvailability("opt", docks_available=2),
        )
        msg = build_briefing_message("Vincent", _make_weather(), d)
        assert "almost full" in msg or "hurry" in msg

    def test_backup_station_mentioned_when_no_ebikes(self):
        d = _make_divvy(
            home_primary=StationAvailability("home", classic_bikes=3, ebikes=0, scooters=0),
            home_backup=StationAvailability("backup", ebikes=2, scooters=1),
        )
        msg = build_briefing_message("Vincent", _make_weather(), d)
        assert "Backup" in msg or "Orleans" in msg

    def test_social_circle_events_included(self):
        events = ["\U0001f382 Mark's birthday (turns 35)", "\U0001f48d Lisa & Tom's anniversary"]
        msg = build_briefing_message("Vincent", _make_weather(), _make_divvy(), todays_events=events)
        assert "Today:" in msg
        assert "Mark's birthday" in msg
        assert "anniversary" in msg

    def test_no_events_no_section(self):
        msg = build_briefing_message("Vincent", _make_weather(), _make_divvy(), todays_events=[])
        assert "Today:" not in msg


class TestOnDemandMessages:
    def test_bikes_message(self):
        d = _make_divvy()
        msg = build_on_demand_bikes_message(d)
        assert "Divvy status" in msg
        assert "ebikes" in msg

    def test_bikes_unavailable(self):
        msg = build_on_demand_bikes_message(None)
        assert "Couldn't fetch" in msg

    def test_weather_message(self):
        w = _make_weather()
        msg = build_on_demand_weather_message(w)
        assert "Weather" in msg
        assert "72\u00b0F" in msg

    def test_weather_unavailable(self):
        msg = build_on_demand_weather_message(None)
        assert "Couldn't fetch" in msg
```

#### `backend/tests/test_briefing_integration.py`

Integration tests with mocked external APIs:

```python
"""Integration tests for the full briefing pipeline with mocked APIs."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.briefing.divvy import DivvyData, NearbyFreeBikes, StationAvailability, build_divvy_data
from src.briefing.engine import BriefingEngine
from src.briefing.weather import WeatherData


@pytest.fixture
def mock_weather():
    return WeatherData(
        temperature=72, feels_like=75, precipitation=0, wind_speed=8,
        wind_gusts=12, humidity=45, weather_code=2, weather_description="Partly cloudy",
        high=82, low=65, feels_like_high=84, feels_like_low=63,
        precip_probability=10, daily_max_wind=12, daily_weather_code=2,
    )


@pytest.fixture
def mock_station_status():
    return {
        "a3a40088-a135-11e9-9cda-0a87ae2ba916": StationAvailability(
            "a3a40088-a135-11e9-9cda-0a87ae2ba916",
            classic_bikes=5, ebikes=3, scooters=2, docks_available=8,
        ),
        "a3b35e21-a135-11e9-9cda-0a87ae2ba916": StationAvailability(
            "a3b35e21-a135-11e9-9cda-0a87ae2ba916",
            classic_bikes=2, ebikes=1, scooters=0, docks_available=12,
        ),
        "2178904806732191280": StationAvailability(
            "2178904806732191280", docks_available=14,
        ),
        "2161159315996441640": StationAvailability(
            "2161159315996441640", docks_available=17,
        ),
    }


@pytest.fixture
def mock_free_bikes():
    return NearbyFreeBikes(ebikes=2, scooters=1)


class TestFullBriefingGeneration:
    """Mock external APIs and test end-to-end briefing generation."""

    @patch("src.briefing.engine.fetch_weather")
    @patch("src.briefing.engine.fetch_station_status")
    @patch("src.briefing.engine.fetch_free_bikes")
    @patch("src.briefing.engine._fetch_todays_events", return_value=[])
    async def test_full_briefing_vincent(
        self, mock_events, mock_fb, mock_ss, mock_w,
        mock_weather, mock_station_status, mock_free_bikes,
    ):
        mock_w.return_value = mock_weather
        mock_ss.return_value = mock_station_status
        mock_fb.return_value = mock_free_bikes

        db = MagicMock()
        settings = MagicMock()
        settings.TIMEZONE = "America/Chicago"
        engine = BriefingEngine(db, settings)

        msg = await engine.get_briefing_for_user("Vincent")
        assert "Good morning Vincent" in msg
        assert "Optiver" in msg
        assert "72\u00b0F" in msg
        assert "3 ebikes" in msg

    @patch("src.briefing.engine.fetch_weather")
    @patch("src.briefing.engine.fetch_station_status")
    @patch("src.briefing.engine.fetch_free_bikes")
    @patch("src.briefing.engine._fetch_todays_events", return_value=[])
    async def test_full_briefing_christianne(
        self, mock_events, mock_fb, mock_ss, mock_w,
        mock_weather, mock_station_status, mock_free_bikes,
    ):
        mock_w.return_value = mock_weather
        mock_ss.return_value = mock_station_status
        mock_fb.return_value = mock_free_bikes

        db = MagicMock()
        settings = MagicMock()
        settings.TIMEZONE = "America/Chicago"
        engine = BriefingEngine(db, settings)

        msg = await engine.get_briefing_for_user("Christianne")
        assert "Good morning Christianne" in msg
        assert "Adyen" in msg
        assert "Optiver" not in msg


class TestPartialFailure:
    """Test graceful degradation when APIs fail."""

    @patch("src.briefing.engine.fetch_weather", return_value=None)
    @patch("src.briefing.engine.fetch_station_status")
    @patch("src.briefing.engine.fetch_free_bikes")
    @patch("src.briefing.engine._fetch_todays_events", return_value=[])
    async def test_weather_down_divvy_ok(
        self, mock_events, mock_fb, mock_ss, mock_w, mock_station_status, mock_free_bikes,
    ):
        mock_ss.return_value = mock_station_status
        mock_fb.return_value = mock_free_bikes

        db = MagicMock()
        settings = MagicMock()
        settings.TIMEZONE = "America/Chicago"
        engine = BriefingEngine(db, settings)

        msg = await engine.get_briefing_for_user("Vincent")
        assert "Weather data unavailable" in msg
        assert "ebikes" in msg  # Divvy data should still be present

    @patch("src.briefing.engine.fetch_weather")
    @patch("src.briefing.engine.fetch_station_status", return_value=None)
    @patch("src.briefing.engine.fetch_free_bikes", return_value=None)
    @patch("src.briefing.engine._fetch_todays_events", return_value=[])
    async def test_divvy_down_weather_ok(
        self, mock_events, mock_fb, mock_ss, mock_w, mock_weather,
    ):
        mock_w.return_value = mock_weather

        db = MagicMock()
        settings = MagicMock()
        settings.TIMEZONE = "America/Chicago"
        engine = BriefingEngine(db, settings)

        msg = await engine.get_briefing_for_user("Vincent")
        assert "72\u00b0F" in msg  # Weather present
        assert "Bike data unavailable" in msg

    @patch("src.briefing.engine.fetch_weather", return_value=None)
    @patch("src.briefing.engine.fetch_station_status", return_value=None)
    @patch("src.briefing.engine.fetch_free_bikes", return_value=None)
    @patch("src.briefing.engine._fetch_todays_events", return_value=[])
    async def test_all_apis_down(self, mock_events, mock_fb, mock_ss, mock_w):
        db = MagicMock()
        settings = MagicMock()
        settings.TIMEZONE = "America/Chicago"
        engine = BriefingEngine(db, settings)

        msg = await engine.get_briefing_for_user("Vincent")
        assert "Good morning Vincent" in msg  # Still sends a greeting
        assert "Weather data unavailable" in msg
        assert "Bike data unavailable" in msg
```

### What to test

```bash
cd /Users/vincent/jarvis/backend
source .venv/bin/activate

# Run only briefing tests
pytest tests/test_clothing.py tests/test_recommendation.py tests/test_message_builder.py tests/test_briefing_integration.py -v

# Run all tests (ensure nothing is broken)
pytest -v

# Lint
ruff check .
```

All tests must pass before proceeding.

### Git commit

```
test(briefing): comprehensive test suite for morning briefing module

- test_clothing.py: all temperature ranges, rain, wind, boundary values
- test_recommendation.py: weather checks, bike availability, partial failure
- test_message_builder.py: per-user personalization, partial failure, formatting
- test_briefing_integration.py: end-to-end with mocked APIs, graceful degradation
```

---

## Step 9: Cron + Skills

Set up the launchd cron trigger and create operational skills for Claude.

### Files to create

#### `deploy/com.jarvis.briefing.plist`

launchd plist for the 07:00 America/Chicago morning briefing. Since the Mac mini system clock is UTC and launchd `StartCalendarInterval` uses local system time, we need to calculate the UTC equivalent.

07:00 CT = 12:00 UTC (CDT, UTC-5) or 13:00 UTC (CST, UTC-6). Since Chicago observes DST, use a shell script that handles the timezone correctly.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.briefing</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/vincent/jarvis/deploy/run_briefing.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <!-- Weekdays only: Monday(1) through Friday(5) -->
        <dict>
            <key>Weekday</key>
            <integer>1</integer>
            <key>Hour</key>
            <integer>12</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key>
            <integer>2</integer>
            <key>Hour</key>
            <integer>12</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key>
            <integer>3</integer>
            <key>Hour</key>
            <integer>12</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key>
            <integer>4</integer>
            <key>Hour</key>
            <integer>12</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Weekday</key>
            <integer>5</integer>
            <key>Hour</key>
            <integer>12</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/Users/vincent/jarvis/logs/briefing.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/vincent/jarvis/logs/briefing.error.log</string>
</dict>
</plist>
```

**Note:** The `Hour` value (12 UTC) maps to 07:00 CDT. When DST ends (November to March), this fires at 06:00 CST. Adjust to `Hour=13` for winter, or use the shell script approach below to always fire at the right local time. The engine also has weekend skip logic as a safety net.

**Alternative (simpler):** If the Mac mini system timezone is set to `America/Chicago` (not UTC), use `Hour=7, Minute=0` directly and remove the weekday entries. Verify with: `sudo systemsetup -gettimezone`. The engine's own weekend check handles Saturday/Sunday skipping.

#### `deploy/run_briefing.sh`

```bash
#!/bin/bash
set -euo pipefail

# Load API key from .env
JARVIS_API_KEY=$(grep JARVIS_API_KEY /Users/vincent/jarvis/.env | cut -d'=' -f2)

echo "[$(date)] Running morning briefing..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "X-API-Key: $JARVIS_API_KEY" \
  http://localhost:8000/api/briefing/run)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "[$(date)] Response: HTTP $HTTP_CODE - $BODY"

if [ "$HTTP_CODE" != "200" ]; then
  echo "[$(date)] ERROR: Briefing engine returned HTTP $HTTP_CODE"
  exit 1
fi

echo "[$(date)] Morning briefing completed successfully"
```

Make executable: `chmod +x deploy/run_briefing.sh`

#### `.claude/skills/morning-briefing`

Operational skill for Claude to generate a morning briefing:

```markdown
# Skill: morning-briefing

## When to use
User asks about the morning briefing, weather + bikes combined, or "what should I wear today?"

## Steps

1. Determine the user's name from CURRENT_USER in the system prompt.
2. Call the on-demand briefing endpoint:
   ```bash
   curl -s -H "X-API-Key: $JARVIS_API_KEY" "http://localhost:8000/api/briefing?user_name={name}"
   ```
3. Extract the `message` field from the JSON response.
4. Send the message text to the user as-is (it's already formatted for Telegram).

## Notes
- The briefing is personalized: Vincent sees Optiver docks, Christianne sees Adyen.
- If the API returns an error, tell the user and suggest trying again in a minute.
- The daily automatic briefing runs at 07:00 CT on weekdays. This skill is for on-demand requests.
```

#### `.claude/skills/check-bikes`

Operational skill for quick Divvy station check:

```markdown
# Skill: check-bikes

## When to use
User asks "are there bikes?", "any bikes available?", "Divvy status", "can I bike?", or any variation about bike availability.

## Steps

1. Call the bikes endpoint:
   ```bash
   curl -s -H "X-API-Key: $JARVIS_API_KEY" http://localhost:8000/api/briefing/bikes
   ```
2. Extract the `message` field from the JSON response.
3. Send the message text to the user as-is.

## Notes
- This is a quick check — no weather, no clothing suggestion. Just bike/dock availability.
- Works at any time of day, not just mornings.
- If the user also asks about weather, use the `morning-briefing` skill instead.
```

### Files to modify

#### `deploy/install.sh` (if exists) — Add briefing plist

Add the briefing plist to the installation script alongside the existing reminder and backend plists:

```bash
# Add to the plist list
for plist in com.jarvis.backend.plist com.jarvis.bot.plist com.jarvis.reminder.plist com.jarvis.briefing.plist; do
  ...
done
```

### What to test

```bash
# Verify the run script works
cd /Users/vincent/jarvis
bash deploy/run_briefing.sh
# Should print "completed successfully" (or "skipped" on weekends)

# Verify skill files are readable
cat .claude/skills/morning-briefing
cat .claude/skills/check-bikes

# Test launchd plist syntax
plutil -lint deploy/com.jarvis.briefing.plist
# Should say "OK"

# Install plist (optional — only when ready to go live)
# cp deploy/com.jarvis.briefing.plist ~/Library/LaunchAgents/
# launchctl load ~/Library/LaunchAgents/com.jarvis.briefing.plist
```

### Git commit

```
feat(briefing): cron trigger and operational skills

- com.jarvis.briefing.plist: launchd cron for 07:00 CT weekdays
- run_briefing.sh: curl trigger for POST /api/briefing/run
- morning-briefing skill: on-demand full briefing via Claude
- check-bikes skill: quick Divvy status check via Claude
```

---

## Summary: File Map

All files created or modified by this plan, organized by step.

### Step 1: Constants + Config

```
backend/src/briefing/__init__.py              -- NEW
backend/src/briefing/constants.py             -- NEW
backend/pyproject.toml                        -- MODIFIED (add httpx to deps)
```

### Step 2: Weather Fetcher

```
backend/src/briefing/weather.py               -- NEW
```

### Step 3: Divvy Fetcher

```
backend/src/briefing/divvy.py                 -- NEW
```

### Step 4: Clothing + Recommendation

```
backend/src/briefing/clothing.py              -- NEW
backend/src/briefing/recommendation.py        -- NEW
```

### Step 5: Message Builder

```
backend/src/briefing/message_builder.py       -- NEW
```

### Step 6: Briefing Engine

```
backend/src/briefing/engine.py                -- NEW
backend/src/engine/telegram_sender.py         -- MODIFIED (add send_to_user)
```

### Step 7: Routes

```
backend/src/briefing/schemas.py               -- NEW
backend/src/routes/briefing.py                -- NEW
backend/src/main.py                           -- MODIFIED (wire briefing router)
```

### Step 8: Tests

```
backend/tests/test_clothing.py                -- NEW
backend/tests/test_recommendation.py          -- NEW
backend/tests/test_message_builder.py         -- NEW
backend/tests/test_briefing_integration.py    -- NEW
```

### Step 9: Cron + Skills

```
deploy/com.jarvis.briefing.plist              -- NEW
deploy/run_briefing.sh                        -- NEW
.claude/skills/morning-briefing               -- NEW
.claude/skills/check-bikes                    -- NEW
deploy/install.sh                             -- MODIFIED (add briefing plist, if exists)
```

---

## Dependency Graph

```
Step 0 (Prerequisites: httpx dep)
  |
  v
Step 1 (Constants)
  |
  +---> Step 2 (Weather Fetcher)
  |       |
  +---> Step 3 (Divvy Fetcher)
  |       |
  v       v
Step 4 (Clothing + Recommendation) <-- depends on Step 2 (WeatherData type)
  |
  v
Step 5 (Message Builder) <-- depends on Steps 2, 3, 4
  |
  v
Step 6 (Briefing Engine) <-- depends on Steps 2, 3, 5 + telegram_sender
  |
  v
Step 7 (Routes) <-- depends on Step 6
  |
  v
Step 8 (Tests) <-- depends on Steps 1-7
  |
  v
Step 9 (Cron + Skills) <-- depends on Step 7
```

Note: Steps 2 and 3 are independent and can be built in parallel. Step 4 depends on Step 2 (uses the `WeatherData` type). Steps 1 through 7 are the build sequence. Step 8 can technically be written alongside each step but is grouped here for clarity. Step 9 depends on routes being live.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Open-Meteo rate limiting or outage | Returns None gracefully; briefing still sends with "Weather data unavailable" note. No API key to expire. |
| Divvy GBFS schema changes (GBFS v2.3 -> v3) | `_parse_station` has fallback for missing `vehicle_types_available`. Monitor GBFS spec changes. |
| Station IDs change (Divvy removes/moves a station) | `is_installed=false` handled gracefully. Station IDs are hardcoded — update constants if needed. |
| Timezone/DST issues with launchd cron | Engine has its own weekend check. Plist note documents UTC offset. Alternative: set Mac mini TZ to Chicago. |
| httpx timeout too aggressive for slow API | 10s is generous for these APIs. If needed, bump `API_TIMEOUT_SECONDS` in constants. |
| Free-floating bike data is noisy (bikes everywhere) | `FREE_BIKE_SEARCH_RADIUS_M = 500` keeps it relevant to walkable distance from home. |
| `send_to_user` function doesn't exist yet in telegram_sender | Step 6 adds it. Clearly documented as a modification. |
| Cross-module dependency on Social Circle (events for today) | `_fetch_todays_events` wrapped in try/except — returns empty list if Social Circle is not ready. No hard dependency. |

---

## Spec Requirements Traceability

| Requirement | Covered In |
|-------------|-----------|
| REQ-001: Daily morning briefing at 07:00 CT | Step 6: BriefingEngine.run(), Step 9: launchd plist |
| REQ-002: Weather section with all fields | Step 2: WeatherData, Step 5: _format_weather_section |
| REQ-003: Clothing suggestion based on conditions | Step 4: get_clothing_suggestion() |
| REQ-004: Divvy home station with vehicle breakdown | Step 3: StationAvailability, Step 5: _format_station_bikes |
| REQ-005: Dock availability at office stations per user | Step 3: DivvyData, Step 5: _format_station_docks |
| REQ-006: Backup station + free-floating check | Step 3: fetch_free_bikes(), Step 5: _format_backup_note |
| REQ-007: Biking recommendation (Yes/No) | Step 4: get_bike_recommendation() |
| REQ-008: On-demand check at any time | Step 7: GET /api/briefing/bikes, GET /api/briefing/weather |
| REQ-009: Per-user personalization (Vincent/Optiver, Christianne/Adyen) | Step 5: build_briefing_message() with user_name parameter |
| NFR-001: Send by 07:05, partial failure handling | Step 6: asyncio.gather, all fetchers return None on failure |
| NFR-002: Parallel fetch with 10s timeout | Step 6: asyncio.gather(return_exceptions=True), Step 1: API_TIMEOUT_SECONDS |
| NFR-003: No API keys | Step 1: constants use free/no-auth APIs |
| AC-001: Both users receive briefing at 07:00 | Step 6: engine iterates user_names_dict, Step 9: cron |
| AC-002: Vincent/Optiver, Christianne/Adyen | Step 5: OFFICE_BY_NAME lookup |
| AC-003: Rainy day recommendation says "No" | Step 4: rain check in get_bike_recommendation(), Step 8: test_rain_current |
| AC-004: Backup station mentioned when no ebikes | Step 5: _format_backup_note(), Step 8: test_backup_station_mentioned |
| AC-005: Weather down, Divvy still works | Step 5/6: partial failure handling, Step 8: test_weather_down_divvy_ok |
| AC-006: On-demand bike check | Step 7: GET /api/briefing/bikes, Step 9: check-bikes skill |
| AC-007: Clothing adjusts for wind chill and humidity | Step 4: uses feels_like temp (which incorporates wind chill + humidity) |
