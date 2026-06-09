"""Morning Briefing constants -- all hardcoded for v1.

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
# Default mapping (Vincent=Optiver, Christianne=Adyen)
# Resolved at message-build time using the user's name from settings
OFFICE_BY_NAME = {
    "Vincent": {"key": "optiver", "station_id": "2178904806732191280", "label": "Optiver"},
    "Christianne": {"key": "adyen", "station_id": "2161159315996441640", "label": "Adyen"},
}

# --- Clothing thresholds (feels-like temperature, Fahrenheit) ---
CLOTHING_THRESHOLDS = [
    (80, "Light and breathable \u2014 shorts and t-shirt. Stay hydrated."),
    (60, "Perfect biking weather \u2014 light layers."),
    (40, "Bring a jacket. Consider gloves for the wind."),
    (25, "Bundle up \u2014 warm jacket, gloves, hat. Cover your ears."),
]
CLOTHING_BRUTAL = "It's brutal out there. Full winter gear or consider transit."
CLOTHING_RAIN = "Rain expected \u2014 bring a rain jacket and fenders help."
CLOTHING_WIND = "Windy \u2014 expect resistance on the ride."

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
PRECIPITATION_WEATHER_CODES = {
    51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
    71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99,
}

# --- Nearby free-floating bike search radius (meters) ---
FREE_BIKE_SEARCH_RADIUS_M = 500
