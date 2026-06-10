# INC-001 — Daily weather forecast ignored in briefing

**Date:** 2026-06-10
**Reported by:** Vincent
**Module:** Morning Briefing (`backend/src/briefing/`)
**Severity:** High — the whole point of the morning briefing is to inform a full-day biking decision; missing the daily forecast defeats the purpose.

## What happened

At 06:31 CT on 2026-06-10, the on-demand weather briefing returned:

```
🌡 Weather: 21°C (feels like 24°C)
↑ High 35°C / ↓ Low 19°C
Clear sky • 48% chance of rain • Wind 10 km/h

👔 Perfect biking weather — light layers.
```

Open-Meteo had reported `current.weather_code = 0` (Clear sky) **and** `daily.weather_code[0] = 95` (Thunderstorm). The daily code was fetched into `WeatherData.daily_weather_code` but never read by any consumer, so the user is told it's clear and bike-perfect on a day with thunderstorms forecast.

## Impact

A user reading the morning briefing and choosing to bike based on "Clear sky • Perfect biking weather" could be caught in a thunderstorm later that day. The briefing exists specifically to inform a full-day decision; the bug silently defeats that.

## Root cause

`WeatherData.daily_weather_code`, `feels_like_high`, `feels_like_low`, and `daily_max_wind` were added to the dataclass and populated from Open-Meteo, but no downstream code reads them:
- `recommendation.py` checks `weather.weather_code` (current only) against `PRECIPITATION_WEATHER_CODES`.
- `clothing.py` checks `weather.weather_code` (current only) for rain.
- `message_builder.py` formats `weather.weather_description` (derived from the current code only).

Net effect: the most important field for a *morning* briefing — what the rest of the day looks like — is dropped on the floor.

## Fix

1. `recommendation.py`: include `daily_weather_code` in the precipitation check, so a thunderstorm or rain code in the daily forecast forces a "don't bike" recommendation with a clear reason.
2. `clothing.py`: include `daily_weather_code` in the `has_rain` check so the user gets a rain-jacket suggestion when the daily forecast indicates precipitation.
3. `message_builder.py`: when the daily forecast differs from current conditions AND indicates precipitation, append the daily description to the detail line (e.g. "Clear sky • thunderstorm forecast • …").

Commit: `fix(briefing): use daily_weather_code in recommendation, clothing, and message`.

## Prevention

- Added rule to `backend/src/briefing/CLAUDE.md`: any field added to `WeatherData` must be consumed by at least one of `clothing.py`, `recommendation.py`, or `message_builder.py` — otherwise drop it from the dataclass. Fetching data we don't use is a silent failure mode.
- Tests TODO (tracked in STATUS.md): unit tests for `recommendation.py` and `clothing.py` must cover the "current clear, daily rainy" case so this regresses loudly.
