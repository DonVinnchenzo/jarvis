# Morning Briefing — Ideation Research

**Date:** 2026-06-09

## Concept

Daily morning briefing sent proactively via Telegram at ~07:00 CT. Includes weather, clothing suggestion for biking, and live Divvy bike/ebike/scooter availability at stations near home and both offices.

## API Research

### Divvy (GBFS v2.3) — Free, no auth

- **Station Status**: `https://gbfs.lyft.com/gbfs/2.3/chi/en/station_status.json`
- **Station Info**: `https://gbfs.lyft.com/gbfs/2.3/chi/en/station_information.json`
- **Free Bike Status**: `https://gbfs.lyft.com/gbfs/2.3/chi/en/free_bike_status.json` (dockless)
- **Vehicle Types**: `https://gbfs.lyft.com/gbfs/2.3/chi/en/vehicle_types.json`
- Refresh rate: 60 seconds TTL
- Vehicle types: classic bike (human), ebike (electric_assist), scooter (electric)

### Weather — Open-Meteo (free, no auth)

- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Fields: temperature, feels-like, precipitation, wind speed/gusts, weather code
- Units: Fahrenheit, mph, inches
- Rate limit: 10,000 requests/day
- No API key needed

### Key Locations

- **Home**: 228 W Hill St, Chicago, IL 60610 (41.8967, -87.6355)
- **Optiver (Vincent)**: 150 S Wacker Dr, Chicago, IL 60606 (41.8795, -87.6368)
- **Adyen (Christianne)**: 350 N Orleans St, Suite 900S, Chicago, IL 60654 (41.8885, -87.6374)

### Key Divvy Stations

**Home:**
- Franklin St & Chicago Ave — `a3a40088-a135-11e9-9cda-0a87ae2ba916` (0.01 mi, basically at the door)
- Orleans St & Chestnut St — `a3b35e21-a135-11e9-9cda-0a87ae2ba916` (0.15 mi, backup)

**Optiver (Vincent drop-off):**
- Riverside Plaza & Adams St — `2178904806732191280` (0.10 mi)
- Franklin St & Adams St — `a3a9df3a-a135-11e9-9cda-0a87ae2ba916` (0.07 mi)

**Adyen (Christianne drop-off):**
- Kingsbury St & Kinzie St 2 — `2161159315996441640` (0.07 mi)
- Orleans St & Merchandise Mart Plaza — `a3a5428e-a135-11e9-9cda-0a87ae2ba916` (0.06 mi)

## Recommendation

Proceed to spec. APIs are free and reliable. Data is structured and easy to consume. Implementation is straightforward — backend calls APIs, formats message, sends via Telegram.
