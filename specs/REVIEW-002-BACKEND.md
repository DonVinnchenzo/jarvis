# Backend Engineering Review: 002-morning-briefing

**Reviewer:** Claude Code
**Date:** 2026-06-09
**Spec:** `/Users/vincent/jarvis/specs/002-morning-briefing.md`

---

## Executive Summary

The Morning Briefing spec is **technically sound with manageable risk**. It reuses established patterns from Social Circle (proactive cron engine) and adds external API integration. The design is pragmatic—hardcoding config for v1 and treating the service as stateless is the right call.

**Overall Assessment:** Spec is **approved for implementation** with 3 blocking issues and 6 suggestions for v1 or v2.

---

## 1. API Integration Review

### Design Assessment

The spec calls three external APIs:
- **Open-Meteo** — Weather forecast (public, no auth)
- **Divvy GBFS** — Bike station status (public, no auth, v2.3 standard)
- **Divvy GBFS system alerts** — Service disruptions (same GBFS endpoint)

#### Findings

| Issue | Severity | Category | Details |
|-------|----------|----------|---------|
| **Missing timeout specification** | **BLOCKING** | API Integration | Spec says "timeout after 10 seconds" (NFR-002) but doesn't specify: Which timeout applies? Sequential calls = 30s worst case? Parallel calls = 10s each? Network stack timeout? Missing from endpoint design. |
| **Partial failure handling vague** | **BLOCKING** | Reliability | NFR-001 says "send partial briefing with whatever data is available" but doesn't define the fallback priority. If Divvy is down but weather is up, should the briefing still say "Bike today? No" (missing data) or "Unavailable"? Current spec is ambiguous. |
| **No retry logic** | Suggestion | Resilience | Spec doesn't mention retries. Open-Meteo might have a blip; single timeout = no message. Consider: `asyncio.timeout(10s)` with 1 automatic retry on timeout (total budget 15-20s). |
| **API version pinning** | Suggestion | Maintenance | Divvy GBFS URL hardcodes v2.3. If Lyft rolls out v2.4, endpoints might change. Good: station IDs are versioned separately. Suggestion: add a spec clause "Monitor GBFS changelog quarterly; update version if v2.4 is announced." |
| **Station ID mutation risk** | Suggestion | Data Integrity | Spec says station IDs "rarely change" (line 118) but doesn't handle the failure case. If Franklin & Chicago station is decommissioned, Divvy returns `is_installed: 0`. Code must check this and skip stations gracefully (log warning). |

---

### Code Pattern Recommendation

The existing Social Circle proactive engine uses a good pattern: exception handling with logging, partial success, and continuation (lines 99-102 in `reminder_engine.py`).

For Morning Briefing, apply the same pattern:

```python
# Pseudocode
async def fetch_weather():
    try:
        return await asyncio.wait_for(
            fetch_open_meteo(...),
            timeout=10
        )
    except asyncio.TimeoutError:
        logger.warning("Weather API timeout")
        return None
    except Exception as e:
        logger.exception("Weather API error: %s", e)
        return None

async def fetch_divvy():
    try:
        return await asyncio.wait_for(
            fetch_gbfs(...),
            timeout=10
        )
    except asyncio.TimeoutError:
        logger.warning("Divvy API timeout")
        return None
    except Exception as e:
        logger.exception("Divvy API error: %s", e)
        return None

async def build_briefing():
    # Parallel fetch with asyncio.gather()
    weather, divvy = await asyncio.gather(
        fetch_weather(),
        fetch_divvy(),
        return_exceptions=False  # Let exceptions bubble if both fail
    )

    # Build message from whatever we have
    if not weather and not divvy:
        return "Both APIs down, briefing unavailable"

    message = ""
    if weather:
        message += format_weather(weather)
    else:
        message += "⚠ Weather data unavailable\n"

    if divvy:
        message += format_divvy(divvy)
    else:
        message += "⚠ Bike availability unavailable\n"

    return message
```

**Action:** Add this code structure and timeout strategy to the spec's Technical Notes section.

---

## 2. Data Model Review

### Assessment

**Decision is sound: No new tables for v1, hardcoding config.**

The rationale (line 225: "Add the config table when there's a second configurable module") is pragmatic. The Morning Briefing module is stateless—all data is fetched fresh on each run. No history needed.

#### Findings

| Issue | Severity | Category | Details |
|-------|----------|----------|---------|
| **`module_config` table premature** | **BLOCKING** | Design | Spec says "Or simply hardcode for v1" (line 223) but then shows a `ModuleConfig` schema (lines 212-221). This is confusing—is it implemented or not? Decision: hardcode. Clarify the spec by removing the `ModuleConfig` schema entirely. It signals future-proofing without v1 value. |
| **No versioning of hardcoded values** | Suggestion | Maintainability | Station IDs are hardcoded in Python. If Divvy retires a station, we need a deploy. Better: Read station IDs from a `briefing_config.json` file in the repo (version-controlled, but not in DB). Fallback: hardcode is acceptable for v1, add to v2 backlog. |
| **No audit trail for manual changes** | Suggestion | Ops | If we hardcode timezones, coordinates, station IDs, and someone edits a Python file by mistake, there's no undo. Suggestion: Add a brief `briefing_config.json` that stores these, with a comment explaining each value and a git diff audit trail. |

**Verdict:** Remove the `ModuleConfig` schema from the spec. Confirm hardcoding for v1. Good call.

---

## 3. Cron Design Review

### Assessment

**Two cron jobs, two different timezones = risk. Needs clarification.**

The spec says:
- Morning briefing: **07:00 CT** (America/Chicago)
- Social Circle reminders: **08:00 Amsterdam** (Europe/Amsterdam)

#### Findings

| Issue | Severity | Category | Details |
|-------|----------|----------|---------|
| **Timezone mismatch in production** | **BLOCKING** | Reliability | Social Circle cron is hardcoded to run at 08:00 Europe/Amsterdam (line 89 in 001-social-circle.md). Morning Briefing should run at 07:00 CT. If both are implemented as launchd jobs on a Mac in Europe, the scheduler is naive UTC or system timezone. How does the cron ensure correct trigger times across timezones? Must specify: launchd vs. systemd vs. custom Python scheduled task with pytz. **Current spec says nothing about cron implementation.** |
| **launchd plist missing from spec** | **BLOCKING** | Implementation | The spec references a "new launchd plist" (line 325, rollout step 2) but provides zero plist example. launchd cannot natively run at "07:00 CT"—it uses naive times. Need either: (a) a Python service that calculates the next 07:00 CT and schedules via launchd StartCalendarInterval, or (b) a dedicated systemd timer (not macOS), or (c) clarify that the backend service will handle scheduling internally. |
| **No heartbeat/health check for morning briefing** | Suggestion | Monitoring | Social Circle has heartbeat monitoring (line 380 in 001-social-circle.md). Morning Briefing should too—if the cron fails, both users should be alerted. Spec says "NFR-001: Briefing must send by 07:05 CT" but doesn't define what happens if it doesn't. Suggestion: Add a heartbeat mechanism (similar to Social Circle) and a Telegram alert if briefing doesn't run by 07:15 CT. |
| **No weekend handling clarification** | Suggestion | Behavior | Spec says "Skip the briefing on weekends (Saturday/Sunday) unless explicitly configured" (line 153). Good decision, but **code must implement this**. The cron job runs daily; the endpoint must check: if today is Saturday/Sunday, skip (don't send). Recommendation: Add a config flag `SKIP_WEEKENDS: bool = True` to hardcoded settings and check in the briefing logic. |

**Action:** Specify launchd plist approach (or alternative scheduler) in the spec. Include heartbeat/alert pattern. Add weekend skip flag.

---

## 4. Endpoint Design Review

### Assessment

The proposed endpoints are clean and follow REST conventions:

```
POST /api/briefing/run              — Cron trigger
GET  /api/briefing?user_id={id}     — On-demand per-user
GET  /api/briefing/bikes             — Divvy status only
GET  /api/briefing/weather           — Weather status only
```

#### Findings

| Issue | Severity | Category | Details |
|-------|----------|----------|---------|
| **`POST /api/briefing/run` auth** | Suggestion | Security | The endpoint is called by cron (launchd) with `X-API-Key` header (inherited from Social Circle pattern). Good. But spec doesn't explicitly state this. Recommendation: Add a note "Called by cron with X-API-Key header (same as /api/reminders/run)." |
| **`GET /api/briefing?user_id={id}` requires user context** | Suggestion | UX | The on-demand endpoint takes `user_id`. But Claude in the bot always knows CURRENT_USER (from system prompt). Should it be optional? Recommendation: If called from the bot, user_id defaults to CURRENT_USER; if called with explicit user_id, return that user's view (Vincent sees Optiver, Christianne sees Adyen). |
| **Missing pagination/caching** | Suggestion | Performance | Multiple on-demand calls within seconds = redundant external API calls. Suggestion: Cache briefing data for 5 minutes per user. If user asks twice in 3 minutes, return cached result. Add `cached_at: datetime` to response. |
| **No endpoint for briefing history** | Suggestion | Audit | Unlike Social Circle reminders (which record SentReminder), Morning Briefing has no history table. If users want to see "what was the briefing 3 days ago?", we can't answer. Suggestion: Optional `briefing_log` table in v2 (store each run's result). For v1, add a note "History not retained; briefing is always live." |

**Verdict:** Endpoints are well-designed. Add authentication clarity and caching consideration.

---

## 5. Performance Review

### Assessment

**Multiple sequential external API calls + Telegram sends = acceptable for daily use, but optimize.**

#### Findings

| Issue | Severity | Category | Details |
|-------|----------|----------|---------|
| **Sequential vs. parallel execution unclear** | **BLOCKING** | Performance | Spec shows two API calls (Open-Meteo, Divvy) but doesn't specify execution order. If sequential: 10s + 10s = 20s worst case (still under 07:05 CT deadline, assuming 07:00 start). If parallel: max(10s, 10s) = 10s. Spec must clarify. Recommendation: Use `asyncio.gather()` to fetch both in parallel; total timeout budget is 10-15 seconds (leaves 45-50 seconds for Telegram send, message building, and DB write before 07:05 deadline). |
| **Telegram send performance** | Suggestion | Performance | Sending two Telegram messages sequentially = 2-4 seconds typical. Parallel would be faster. Recommendation: Use `asyncio.gather()` to send both messages in parallel (same pattern as Social Circle `send_to_all_users`). Already implemented well in Social Circle (line 22 in `telegram_sender.py` returns before all sends complete—can be made async gather for true parallelism). |
| **No connection pooling mentioned** | Suggestion | Scalability | Open-Meteo and Divvy calls use single `httpx` or `aiohttp` client per run. Good. But no mention of connection reuse. Recommendation: Create a module-level HTTP client session (reused across runs) rather than creating a new one per call. This is microoptimization but good practice. |
| **Cold start on cron** | Suggestion | UX | If the backend service is asleep or slow to startup, the first call to `/api/briefing/run` might exceed 5-second timeout on the cron job itself. Recommendation: Use a lightweight Python script (not FastAPI) for the launchd cron that calls the endpoint with a longer timeout (e.g., 30s). Or ensure backend is always running (managed by launchd separately). |

**Action:** Specify parallel fetch strategy. Add note on HTTP client reuse.

---

## 6. Reliability & Error Handling

### Assessment

**Graceful degradation is good. Station ID mutation and API format changes need safeguards.**

#### Findings

| Issue | Severity | Category | Details |
|-------|----------|----------|---------|
| **Divvy station format changes** | Suggestion | Resilience | Divvy GBFS returns station_status with fields like `num_bikes_available`, `num_ebikes_available`, etc. If Lyft changes field names (v2.4 rolls out), parsing breaks. Recommendation: Validate response structure before parsing. Example: Check that `station_status.json` has `data` and `data.stations` arrays. Log a clear error if schema changes. |
| **Weather code interpretation** | Suggestion | Data Validation | Open-Meteo returns `weather_code` (integer). Spec doesn't mention how to handle unknown codes. Recommendation: Map weather_code to a description (e.g., "Clear" for 0, "Cloudy" for 1-3, "Rainy" for 45+, etc.). Add a fallback: if code is unknown, use the current temperature + feels-like to infer ("If temp < 32°F, assume cold; if precipitation > 0%, assume rainy"). |
| **No circuit breaker for APIs** | Suggestion | Fault Tolerance | If Open-Meteo goes down for 24 hours, every morning briefing hits the 10s timeout and returns partial data. Suggestion: Add a circuit breaker (fail-fast after 3 consecutive failures). If Open-Meteo fails 3 times, skip it for 1 hour and return cached data or a placeholder. See `pybreaker` library. |
| **Message truncation if data is huge** | Suggestion | UX | Telegram message limit is ~4,096 characters. If the briefing is very verbose (many stations, long descriptions), it might exceed the limit and fail to send. Recommendation: Trim message to 3,900 chars with an ellipsis, or split into multiple messages. Test with maximum reasonable data. |

**Verdict:** Add validation, caching fallback, and message truncation safeguards.

---

## 7. Code Reuse with Social Circle

### Assessment

**High reuse potential. Patterns are clear and should be applied directly.**

#### Findings

| Issue | Severity | Category | Details |
|-------|----------|----------|---------|
| **Telegram send pattern reusable** | Suggestion | DRY | Social Circle's `send_to_all_users()` (line 8 in `telegram_sender.py`) sends to all whitelisted users. Morning Briefing can reuse this directly. However, it doesn't support **per-user personalization**. Vincent sees Optiver, Christianne sees Adyen. Current function sends the same message to all. **Need a new overload:** `send_briefing_to_user(message: str, user_id: int)` that sends a personalized message to one user. Recommendation: Extend `telegram_sender.py` with a new function or add a `personalize_fn` parameter to the existing function. |
| **Proactive engine pattern reusable** | Suggestion | Architecture | The reminder_engine.py structure (async run, load configs, iterate events, send, record, log) is generic and could be reused. Morning Briefing could follow a similar pattern: `BriefingEngine` class with methods `async run(user_id, today)`. This ensures consistency and makes testing easier. |
| **Message builder pattern** | Suggestion | Code Quality | Social Circle has `message_builder.py`. Morning Briefing should have a similar module: `briefing_message_builder.py` with functions like `build_weather_section()`, `build_bikes_section()`, `build_recommendation()`. This keeps the engine logic clean and message formatting testable. |
| **Config management** | **BLOCKING** | Architecture | Social Circle uses `get_settings()` from `config.py` (Pydantic BaseSettings). Morning Briefing should follow the same pattern. For v1, hardcode the briefing config as class-level constants in the BriefingEngine (or a separate `briefing_config.py` file). **Do not create a ModuleConfig database table yet.** Make it easy to migrate to a config table in v2. |

**Verdict:** Create `briefing_engine.py`, `briefing_message_builder.py`, and extend `telegram_sender.py` for personalization. Reuse pattern from Social Circle.

---

## Summary Table

| # | Finding | Severity | Category | Status |
|---|---------|----------|----------|--------|
| 1 | Missing timeout specification (sequential vs. parallel) | **BLOCKING** | API Integration | Clarify in spec |
| 2 | Partial failure fallback priority undefined | **BLOCKING** | Reliability | Define priority in spec |
| 3 | ModuleConfig schema shown but not implemented | **BLOCKING** | Design | Remove schema, confirm hardcoding |
| 4 | Timezone/cron implementation unspecified | **BLOCKING** | Reliability | Add launchd plist approach |
| 5 | Divvy station ID mutation handling missing | **BLOCKING** | Error Handling | Add `is_installed` check |
| 6 | Endpoint auth not explicitly documented | Suggestion | Security | Document X-API-Key requirement |
| 7 | No retry logic for API timeouts | Suggestion | Resilience | Consider 1 retry on timeout |
| 8 | API version pinning (GBFS v2.3) maintenance | Suggestion | Maintenance | Monitor Divvy changelog |
| 9 | Weekend skip config not mentioned in code | Suggestion | Behavior | Add SKIP_WEEKENDS flag |
| 10 | Per-user personalization (Telegram send) | Suggestion | Code Reuse | Extend telegram_sender.py |
| 11 | Parallel fetch strategy unspecified | Suggestion | Performance | Use asyncio.gather() |
| 12 | Connection pooling not mentioned | Suggestion | Scalability | Reuse HTTP client session |
| 13 | Divvy GBFS schema change handling | Suggestion | Resilience | Validate response structure |
| 14 | Weather code interpretation fallback missing | Suggestion | Data Validation | Add code→description mapping |
| 15 | Circuit breaker for API failures | Suggestion | Fault Tolerance | Add after 3 consecutive failures |
| 16 | Telegram message truncation (4K limit) | Suggestion | UX | Trim to 3,900 chars if needed |
| 17 | Caching for on-demand briefing calls | Suggestion | Performance | Cache 5 minutes per user |
| 18 | Heartbeat/alert if morning briefing misses | Suggestion | Monitoring | Extend from Social Circle pattern |

---

## Recommendations for Implementation

### Phase 1: Spec Revision (Before Coding)

1. **Remove `ModuleConfig` schema.** Confirm hardcoding decision.
2. **Specify parallel fetch with asyncio.gather().** Set timeout budget: 10-15 seconds total for external APIs.
3. **Define partial failure priority:** Weather > Divvy > Both Missing. If both APIs fail, send "Briefing unavailable, both services down" at 07:05 CT anyway (don't skip).
4. **Add launchd plist example.** Show how to schedule at 07:00 CT on a Mac.
5. **Add Divvy station validation.** Check `is_installed` field. Skip decommissioned stations gracefully.
6. **Add weekend skip flag** to hardcoded config.
7. **Add heartbeat monitoring** (like Social Circle) with 07:15 CT alert if briefing didn't run.

### Phase 2: Implementation

1. **Create `src/modules/briefing/` directory** with:
   - `engine.py` — BriefingEngine class (async run method)
   - `message_builder.py` — Format weather, bikes, recommendation sections
   - `api_client.py` — Wrapper around Open-Meteo and Divvy GBFS calls with timeouts
   - `config.py` — Hardcoded settings (station IDs, timezone, coordinates)

2. **Extend `src/engine/telegram_sender.py`** with:
   - `send_briefing_to_user(message, user_id)` — Per-user personalization

3. **Add endpoints** in `src/routes/briefing.py`:
   - `POST /api/briefing/run` — Cron trigger (calls engine.run())
   - `GET /api/briefing?user_id={id}` — On-demand (calls engine.build_for_user(user_id))

4. **Add launchd plist** in `ops/com.jarvis.briefing.plist` for 07:00 CT trigger.

5. **Tests**:
   - Unit: Clothing logic, biking recommendation, message formatting
   - Integration: Mock external APIs, test parallel fetch, partial failure
   - E2E: Seed with test users, verify messages arrive by 07:05 CT

### Phase 3: Monitoring

1. Add heartbeat check (07:15 CT alert).
2. Add Datadog or CloudWatch metrics for API response times.
3. Add Telegram alert if station goes offline (is_installed: 0).

---

## Blocking Issues Summary

Before coding begins, resolve these 6 blocking issues:

1. **Timeout strategy:** Sequential or parallel? Specify 10-15 second budget.
2. **Partial failure priority:** Define which API failure is acceptable vs. critical.
3. **ModuleConfig clarity:** Remove schema or implement; don't show unused code.
4. **Cron implementation:** Provide launchd plist or alternative scheduler spec.
5. **Station decommissioning:** Add is_installed check and graceful skip.
6. **Divvy station ID mutation:** Test that code handles missing stations.

---

## Final Verdict

**Spec is Approved for Implementation with 6 Blocking Issues Resolved.**

The design is sound. Reusing the Social Circle proactive engine pattern is the right call. Hardcoding config for v1 is pragmatic. External API integration is straightforward with good error handling.

The blocking issues are clarifications, not architectural flaws. Once resolved, implementation should be smooth.

**Estimated effort:** 40-60 hours (backend + tests + ops/cron setup).

---

## Appendix: Suggested Code Skeleton

```python
# src/modules/briefing/engine.py
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.modules.briefing.api_client import fetch_weather, fetch_divvy
from src.modules.briefing.message_builder import build_briefing_message
from src.engine.telegram_sender import send_briefing_to_user

class BriefingEngine:
    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    async def run(self, today: date | None = None) -> dict:
        """Cron trigger: build and send briefing to both users."""
        if today is None:
            today = datetime.now(ZoneInfo(self.settings.TIMEZONE)).date()

        # Skip weekends
        if self.settings.SKIP_WEEKENDS and today.weekday() >= 5:
            logger.info("Skipping briefing on weekend")
            return {"status": "skipped_weekend"}

        # Parallel fetch
        weather, divvy = await asyncio.gather(
            fetch_weather(),
            fetch_divvy(),
            return_exceptions=False
        )

        for user_id in self.settings.allowed_user_ids_list:
            message = build_briefing_message(
                weather=weather,
                divvy=divvy,
                user_id=user_id,
                settings=self.settings
            )
            await send_briefing_to_user(message, user_id, self.settings)

        return {"status": "completed"}
```

---

**Reviewed by:** Claude Code
**Date:** 2026-06-09
**Status:** Ready for Implementation (pending blocking issue resolution)
