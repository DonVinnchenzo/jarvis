# Morning Briefing

**Status:** Approved
**Author:** Claude Code
**Date:** 2026-06-09

---

## Overview

A daily proactive morning message sent to both Vincent and Christianne via Telegram at 07:00 CT. Includes weather forecast, clothing/gear recommendation for biking to work, and live Divvy bike availability at stations near home and both offices.

This is the second Jarvis module. It reuses the proactive engine pattern from Social Circle (cron trigger → build message → send to both users) but adds external API calls for real-time data.

---

## Requirements

### Functional Requirements

- [ ] **REQ-001:** Daily morning briefing sent to both users at 07:00 America/Chicago via Telegram.
- [ ] **REQ-002:** Weather section includes: current temperature, feels-like temperature, high/low for the day, precipitation probability, wind speed, and a human-readable weather description.
- [ ] **REQ-003:** Clothing suggestion based on weather conditions — optimized for biking. Accounts for feels-like temperature, rain, wind, and season.
- [ ] **REQ-004:** Divvy section shows live bike availability at the home station (Franklin St & Chicago Ave) — number of classic bikes, ebikes, and scooters.
- [ ] **REQ-005:** Divvy section also shows dock availability at each user's office station — Vincent's (Riverside Plaza & Adams) and Christianne's (Kingsbury St & Kinzie St 2). Empty docks = space to park your bike when you arrive. If docks are full, you can't return your bike.
- [ ] **REQ-006:** If no ebikes or scooters are available at home station, check the backup station (Orleans St & Chestnut St) and nearby free-floating vehicles.
- [ ] **REQ-007:** Biking recommendation: "Bike today? Yes/No" based on weather (no rain, wind < 20 mph, feels-like between 25°F and 100°F) and bike availability (at least 1 vehicle at home station).
- [ ] **REQ-008:** On-demand check — user can ask "are there bikes available?" or "what's the weather?" at any time, not just the morning briefing.
- [ ] **REQ-009:** The message is personalized per user — Vincent sees Optiver dock status, Christianne sees Adyen dock status. Both see home station and weather.
- [x] **~~REQ-010~~:** ~~System alerts from Divvy~~ — **Moved to v2.** Not worth the complexity for launch. The system_alerts endpoint is often empty and alert formatting is unpredictable.

### Non-Functional Requirements

- [ ] **NFR-001:** Briefing must send by 07:05 CT. If external APIs are down, send a partial briefing with whatever data is available + a note about what's missing. Priority order: weather first (most useful alone), Divvy second.
- [ ] **NFR-002:** External API calls fetched in parallel via `asyncio.gather(return_exceptions=True)` with 10-second `httpx` timeout per call. Each API failure is independent — one failing doesn't block the other.
- [ ] **NFR-003:** No API keys stored for weather or Divvy — both are free/no-auth APIs.

---

## Acceptance Criteria

- [ ] **AC-001:** At 07:00 CT, both Vincent and Christianne receive a Telegram message with weather + bike availability.
- [ ] **AC-002:** Vincent's message shows dock availability at Riverside Plaza & Adams (Optiver). Christianne's shows Kingsbury & Kinzie 2 (Adyen).
- [ ] **AC-003:** On a rainy day, the biking recommendation says "No" with reason.
- [ ] **AC-004:** If no ebikes at home station, the message mentions the backup station.
- [ ] **AC-005:** If Open-Meteo is down, the message still includes Divvy data with a note "Weather data unavailable."
- [ ] **AC-006:** User asks "any bikes right now?" at 3pm — gets live Divvy data for all stations.
- [ ] **AC-007:** Clothing suggestion adjusts for wind chill in winter and humidity in summer.

---

## Technical Notes

### External APIs

**Open-Meteo (weather):**
```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=41.8967&longitude=-87.6355
  &current=temperature_2m,apparent_temperature,precipitation,wind_speed_10m,wind_gusts_10m,weather_code,relative_humidity_2m
  &daily=temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_probability_max,wind_speed_10m_max,weather_code
  &temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch
  &timezone=America/Chicago&forecast_days=1
```

**Divvy GBFS v2.3:**
```
GET https://gbfs.lyft.com/gbfs/2.3/chi/en/station_status.json
GET https://gbfs.lyft.com/gbfs/2.3/chi/en/free_bike_status.json
GET https://gbfs.lyft.com/gbfs/2.3/chi/en/system_alerts.json
```

### Station IDs

```python
STATIONS = {
    "home": {
        "primary": "a3a40088-a135-11e9-9cda-0a87ae2ba916",  # Franklin & Chicago
        "backup":  "a3b35e21-a135-11e9-9cda-0a87ae2ba916",  # Orleans & Chestnut
    },
    "optiver": {
        "dropoff": "2178904806732191280",  # Riverside Plaza & Adams
    },
    "adyen": {
        "dropoff": "2161159315996441640",  # Kingsbury & Kinzie 2
    },
}
```

### Clothing Logic

```
feels_like >= 80°F → "Light and breathable — shorts and t-shirt. Stay hydrated."
feels_like 60-79°F → "Perfect biking weather — light layers."
feels_like 40-59°F → "Bring a jacket. Consider gloves for the wind."
feels_like 25-39°F → "Bundle up — warm jacket, gloves, hat. Cover your ears."
feels_like < 25°F  → "It's brutal out there. Full winter gear or consider transit."

if precipitation > 0 or precip_probability > 60%:
    append "Rain expected — bring a rain jacket and fenders help."

if wind_speed > 15 mph:
    append "Windy — expect resistance on the ride."
```

### Fetch Strategy

All external API calls run in parallel via `asyncio.gather(return_exceptions=True)`:

```python
weather, station_status, free_bikes = await asyncio.gather(
    fetch_weather(),        # Open-Meteo, 10s timeout
    fetch_station_status(), # Divvy GBFS, 10s timeout
    fetch_free_bikes(),     # Divvy GBFS, 10s timeout
    return_exceptions=True,
)
# Each result is checked: if isinstance(result, Exception), that section shows fallback text
```

### Station Decommissioning

Before reporting availability, check `is_installed` and `is_renting`/`is_returning` from station_status. If a station is decommissioned (`is_installed: 0`), show "Station temporarily unavailable" instead of zero bikes. This handles station closures gracefully.

### Patterns to Follow

- Reuses the proactive engine cron pattern from Social Circle
- New endpoint: `POST /api/briefing/run` (called by cron at 07:00 CT)
- On-demand: `GET /api/briefing?user_id={id}` (called by Claude when user asks)
- External API calls use `httpx.AsyncClient` with 10s timeout

### Constraints

- Open-Meteo and Divvy GBFS are free, no-auth APIs. No keys to manage.
- Home address: 228 W Hill St, Chicago, IL 60610
- Vincent works at Optiver (150 S Wacker Dr). Christianne works at Adyen (350 N Orleans St).
- Station IDs are hardcoded — they rarely change. If a station is removed, Divvy returns it as `is_installed: 0`.
- **Two cron timezones on one Mac**: Social Circle reminder cron runs at 08:00 Europe/Amsterdam. Morning Briefing cron runs at 07:00 America/Chicago. Both use launchd plists with `StartCalendarInterval`. The Mac mini system clock is UTC; each plist specifies its own time. Alternatively, both plists use UTC times calculated from their target timezones.

---

## Dependencies

### Depends On
- Backend running (FastAPI)
- Telegram bot token (same as Social Circle)
- Internet access for external API calls

### Blocked By
- Nothing (can be built independently of Social Circle)

### Blocks
- Nothing

---

## Out of Scope

- **Route planning** (turn-by-turn bike directions) — use Google Maps
- **CTA/transit alternative** — future enhancement if biking isn't feasible
- **Multi-day forecast** — just today's weather, keep it simple
- **Historical weather tracking** — no need to store weather data
- **Bike reservation** — Divvy doesn't offer an API for this
- **Evening commute check** — v2 enhancement. An afternoon/evening push with updated bike availability for the ride home. For now, users can ask on-demand via REQ-008.
- **Divvy system alerts** — v2. The system_alerts endpoint is often empty and alert formats vary. Not worth parsing for launch.

---

## Open Questions

1. **Q:** Should the briefing also include Social Circle reminders for the day?
   **A:** Yes — if there are events today (birthdays, etc.), append them to the morning briefing. Cross-module integration. Keeps it to one morning message instead of two.

2. **Q:** Different send times for weekends?
   **A:** Skip the briefing on weekends (Saturday/Sunday) unless explicitly configured. No commute on weekends.

3. **Q:** What if both users leave at different times?
   **A:** Send at 07:00 for both. If one wants an earlier/later time, we add per-user config in v2.

---

## User Stories

### Story 1: Morning commute decision

**As** Vincent
**I want** a morning message telling me the weather and if bikes are available
**So that** I know whether to bike or take the L to Optiver

### Story 2: Dress for the ride

**As** Christianne
**I want** a clothing suggestion based on today's weather
**So that** I know what to wear for biking to Adyen

### Story 3: Mid-day check

**As** Vincent
**I want** to ask Jarvis "are there bikes?" at any time
**So that** I can check availability before heading out for lunch or leaving work

### Story 4: Rainy day heads-up

**As** Christianne
**I want** to know if rain is expected in the morning
**So that** I can bring a rain jacket or choose transit instead

---

## API / Interface

### Backend Endpoints

```
POST /api/briefing/run              — Trigger morning briefing (called by cron)
GET  /api/briefing?user_id={id}     — Generate briefing for a specific user (on-demand)
GET  /api/briefing/bikes             — Get current Divvy status for all tracked stations
GET  /api/briefing/weather           — Get current weather data
```

### Operational Skills

Claude uses these when users interact:

- `morning-briefing` — Show weather, bikes, and clothing suggestion
- `check-bikes` — Quick Divvy station status check

---

## Data Model

No new database tables needed. This module is stateless — it fetches live data from external APIs every time.

All configuration (station IDs, coordinates, send time, clothing thresholds) is hardcoded in a constants module for v1. A `ModuleConfig` table can be added when there are multiple configurable modules.

---

## Client Requirements

**Clients:** Telegram bot (both users). Per-user personalization (different office stations).

---

## Security Considerations

- [ ] No API keys stored (Open-Meteo and Divvy are free/no-auth)
- [ ] Location data (home address, office addresses) hardcoded in backend, not exposed via API
- [ ] External API calls use HTTPS

---

## Testing Strategy

### Unit Tests
- **Clothing logic** — test all temperature ranges, rain, wind combinations
- **Biking recommendation** — edge cases: exactly 20 mph wind, 0 bikes, rain + no wind
- **Message formatting** — verify output for various weather conditions
- **API timeout handling** — mock API timeout, verify graceful fallback

### Integration Tests
- **Full briefing generation** — mock external APIs, verify complete message
- **Partial failure** — mock weather API failure, verify Divvy data still included
- **Per-user personalization** — verify Vincent gets Optiver, Christianne gets Adyen

---

## Message Format

### Morning Briefing (Vincent)

```
Good morning Vincent! ☀️

🌡 Weather: 72°F (feels like 75°F)
↑ High 82°F / ↓ Low 65°F
Partly cloudy • 10% chance of rain • Wind 8 mph

👔 Perfect biking weather — light layers.

🚲 Bikes at Franklin & Chicago (home):
   3 ebikes • 2 scooters • 5 classic bikes

📍 Docks at Riverside Plaza & Adams (Optiver):
   14 empty docks — plenty of room

✅ Bike today? Yes — great conditions and bikes available!
```

### Morning Briefing (Christianne)

```
Good morning Christianne! 🌤

🌡 Weather: 72°F (feels like 75°F)
↑ High 82°F / ↓ Low 65°F
Partly cloudy • 10% chance of rain • Wind 8 mph

👔 Perfect biking weather — light layers.

🚲 Bikes at Franklin & Chicago (home):
   3 ebikes • 2 scooters • 5 classic bikes

📍 Docks at Kingsbury & Kinzie (Adyen):
   17 empty docks — plenty of room

✅ Bike today? Yes — great conditions and bikes available!
```

### Rainy Day

```
Good morning Vincent! 🌧

🌡 Weather: 58°F (feels like 52°F)
↑ High 61°F / ↓ Low 49°F
Rain • 85% chance of rain • Wind 15 mph

👔 Bring a rain jacket. Warm layers underneath. Consider gloves.

🚲 Bikes at Franklin & Chicago (home):
   1 ebike • 0 scooters • 3 classic bikes

📍 Docks at Riverside Plaza & Adams (Optiver):
   18 empty docks

❌ Bike today? Probably not — rain expected all morning.
```

---

## Rollout Plan

1. **Backend: briefing module** — Weather fetcher, Divvy fetcher, message builder, clothing logic, biking recommendation. New endpoints.
2. **Cron: 07:00 CT trigger** — New launchd plist or add to existing reminder cron.
3. **Skills: morning-briefing, check-bikes** — For on-demand queries via Claude.
4. **Test & go live** — Verify for a few days, adjust clothing logic based on feedback.

---

## References

- `Ideation/MORNING-BRIEFING-RESEARCH.md` — API research and station lookups
- `specs/001-social-circle.md` — Proactive engine pattern
- Open-Meteo docs: https://open-meteo.com/en/docs
- Divvy GBFS: https://gbfs.lyft.com/gbfs/2.3/chi/gbfs.json

---

## Changelog

- 2026-06-09 — Claude Code — Initial draft
- 2026-06-09 — Claude Code — Resolved review blocking issues: removed ModuleConfig schema contradiction, specified parallel fetch strategy (asyncio.gather), added station decommissioning handling, clarified dock messaging, moved REQ-010 (system alerts) to v2, documented evening commute as v2, added cron timezone note. Status → Approved.
