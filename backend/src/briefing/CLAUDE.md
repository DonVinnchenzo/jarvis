# CLAUDE.md — Morning Briefing module

## Rule: every `WeatherData` field must be consumed

If you add a field to `WeatherData` (in `weather.py`), at least one of
`clothing.py`, `recommendation.py`, or `message_builder.py` must read it.
Fetching data we don't display or act on is a silent failure mode — it
looks like the feature works while the user gets the wrong answer.

**See:** `docs/incidents/INC-001-daily-weather-code-ignored.md`. The bug
was that `daily_weather_code` was fetched but no consumer read it, so a
"Clear sky, bike today!" briefing went out on a thunderstorm-forecast day.

## Rule: a morning briefing decides the whole day

Clothing suggestions, biking recommendations, and the weather detail line
must consider the **daily** forecast, not just the current reading. The
user reads this once at 07:00 CT and decides their full day from it.
Anywhere we currently check `weather.weather_code`, also check
`weather.daily_weather_code` against `PRECIPITATION_WEATHER_CODES`.
