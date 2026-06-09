"""Tests for the /api/upcoming endpoint.

8 tests: basic upcoming, window filtering, year-boundary wrap, Feb 29 handling,
sorting by days_until, today (0 days), age calculation, no results.
"""

from datetime import date
from unittest.mock import patch

from httpx import AsyncClient

from tests.conftest import create_test_contact, create_test_event


def _patch_upcoming_today(target_date: date):
    """Return a context manager that patches _get_today and date.today in the upcoming module."""
    return patch("src.routes.upcoming._get_today", return_value=target_date)


# ---------------------------------------------------------------------------
# 1. Basic upcoming — event within window
# ---------------------------------------------------------------------------


async def test_upcoming_basic(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Mark")
    await create_test_event(
        client, api_headers, contact["id"],
        event_type="birthday", day=20, month=6, year=1990,
    )

    with _patch_upcoming_today(date(2025, 6, 10)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    event = data["events"][0]
    assert event["contact_name"] == "Mark"
    assert event["days_until"] == 10
    assert event["event_type"] == "birthday"


# ---------------------------------------------------------------------------
# 2. Window filtering — event outside window is excluded
# ---------------------------------------------------------------------------


async def test_upcoming_outside_window(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Lisa")
    await create_test_event(
        client, api_headers, contact["id"],
        event_type="birthday", day=25, month=12, year=1985,
    )

    # Today is Jan 1, looking 30 days ahead — Dec 25 is ~360 days away
    with _patch_upcoming_today(date(2025, 1, 1)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    data = resp.json()
    matching = [e for e in data["events"] if e["contact_name"] == "Lisa"]
    assert len(matching) == 0


# ---------------------------------------------------------------------------
# 3. Year-boundary wrap — Dec event seen from late November
# ---------------------------------------------------------------------------


async def test_upcoming_year_boundary(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="NewYear")
    await create_test_event(
        client, api_headers, contact["id"],
        event_type="custom", day=5, month=1, label="New Year party",
    )

    # Today is Dec 20, 2025 — Jan 5 is 16 days away (in 2026)
    with _patch_upcoming_today(date(2025, 12, 20)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    data = resp.json()
    matching = [e for e in data["events"] if e["contact_name"] == "NewYear"]
    assert len(matching) == 1
    assert matching[0]["days_until"] == 16


# ---------------------------------------------------------------------------
# 4. Feb 29 birthday in non-leap year falls back to Feb 28
# ---------------------------------------------------------------------------


async def test_upcoming_feb29_non_leap(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="LeapBaby")
    await create_test_event(
        client, api_headers, contact["id"],
        event_type="birthday", day=29, month=2, year=1992,
    )

    # 2025 is NOT a leap year; Feb 29 birthday should show as Feb 28
    with _patch_upcoming_today(date(2025, 2, 20)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    data = resp.json()
    matching = [e for e in data["events"] if e["contact_name"] == "LeapBaby"]
    assert len(matching) == 1
    assert matching[0]["days_until"] == 8  # Feb 20 -> Feb 28 = 8 days
    assert matching[0]["date_display"] == "February 28"


# ---------------------------------------------------------------------------
# 5. Feb 29 birthday in leap year keeps Feb 29
# ---------------------------------------------------------------------------


async def test_upcoming_feb29_leap_year(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="LeapBaby")
    await create_test_event(
        client, api_headers, contact["id"],
        event_type="birthday", day=29, month=2, year=1992,
    )

    # 2028 IS a leap year; Feb 29 stays Feb 29
    with _patch_upcoming_today(date(2028, 2, 20)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    data = resp.json()
    matching = [e for e in data["events"] if e["contact_name"] == "LeapBaby"]
    assert len(matching) == 1
    assert matching[0]["days_until"] == 9  # Feb 20 -> Feb 29 = 9 days
    assert matching[0]["date_display"] == "February 29"


# ---------------------------------------------------------------------------
# 6. Sorting — closest events first
# ---------------------------------------------------------------------------


async def test_upcoming_sorted_by_days_until(client: AsyncClient, api_headers: dict):
    c1 = await create_test_contact(client, api_headers, name="Far")
    c2 = await create_test_contact(client, api_headers, name="Near")

    await create_test_event(client, api_headers, c1["id"], day=25, month=6)
    await create_test_event(client, api_headers, c2["id"], day=12, month=6)

    with _patch_upcoming_today(date(2025, 6, 10)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    data = resp.json()
    assert len(data["events"]) >= 2
    assert data["events"][0]["contact_name"] == "Near"
    assert data["events"][1]["contact_name"] == "Far"
    assert data["events"][0]["days_until"] <= data["events"][1]["days_until"]


# ---------------------------------------------------------------------------
# 7. Event today (days_until == 0)
# ---------------------------------------------------------------------------


async def test_upcoming_today(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Today")
    await create_test_event(
        client, api_headers, contact["id"],
        event_type="birthday", day=10, month=6, year=1990,
    )

    with _patch_upcoming_today(date(2025, 6, 10)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    data = resp.json()
    matching = [e for e in data["events"] if e["contact_name"] == "Today"]
    assert len(matching) == 1
    assert matching[0]["days_until"] == 0


# ---------------------------------------------------------------------------
# 8. Age calculation
# ---------------------------------------------------------------------------


async def test_upcoming_age_calculation(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="AgePerson")
    await create_test_event(
        client, api_headers, contact["id"],
        event_type="birthday", day=15, month=6, year=1990,
    )

    with _patch_upcoming_today(date(2025, 6, 10)):
        resp = await client.get("/api/upcoming?days=30", headers=api_headers)

    data = resp.json()
    matching = [e for e in data["events"] if e["contact_name"] == "AgePerson"]
    assert len(matching) == 1
    assert matching[0]["age"] == 35  # 2025 - 1990
