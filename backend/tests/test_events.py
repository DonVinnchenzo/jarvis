"""Tests for the events CRUD endpoints.

9 tests: create, update, delete, create with label, invalid event_type,
invalid day/month, event on non-existent contact, child_birthday with child_id,
and cascade delete when contact is deleted.
"""

import uuid

from httpx import AsyncClient

from tests.conftest import create_test_contact, create_test_event

# ---------------------------------------------------------------------------
# 1. Create an event
# ---------------------------------------------------------------------------


async def test_create_event(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)
    event = await create_test_event(
        client, api_headers, contact["id"],
        event_type="birthday", day=14, month=6, year=1990,
    )
    assert event["event_type"] == "birthday"
    assert event["day"] == 14
    assert event["month"] == 6
    assert event["year"] == 1990
    assert event["recurring"] is True
    assert event["contact_id"] == contact["id"]


# ---------------------------------------------------------------------------
# 2. Create event with custom label
# ---------------------------------------------------------------------------


async def test_create_event_with_label(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)
    event = await create_test_event(
        client, api_headers, contact["id"],
        event_type="custom", day=1, month=1, label="New Year's party",
    )
    assert event["label"] == "New Year's party"
    assert event["event_type"] == "custom"


# ---------------------------------------------------------------------------
# 3. Update an event
# ---------------------------------------------------------------------------


async def test_update_event(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)
    event = await create_test_event(client, api_headers, contact["id"])

    resp = await client.put(
        f"/api/events/{event['id']}",
        json={"day": 15, "month": 7},
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["day"] == 15
    assert data["month"] == 7


# ---------------------------------------------------------------------------
# 4. Delete an event
# ---------------------------------------------------------------------------


async def test_delete_event(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)
    event = await create_test_event(client, api_headers, contact["id"])

    resp = await client.delete(f"/api/events/{event['id']}", headers=api_headers)
    assert resp.status_code == 204

    # Verify gone
    resp = await client.delete(f"/api/events/{event['id']}", headers=api_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. Invalid event_type
# ---------------------------------------------------------------------------


async def test_invalid_event_type(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)
    resp = await client.post(
        f"/api/contacts/{contact['id']}/events",
        json={
            "event_type": "invalid_type",
            "day": 1,
            "month": 1,
        },
        headers=api_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 6. Invalid day/month
# ---------------------------------------------------------------------------


async def test_invalid_day_month(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)

    # Day > 31
    resp = await client.post(
        f"/api/contacts/{contact['id']}/events",
        json={"event_type": "birthday", "day": 32, "month": 6},
        headers=api_headers,
    )
    assert resp.status_code == 422

    # Month > 12
    resp = await client.post(
        f"/api/contacts/{contact['id']}/events",
        json={"event_type": "birthday", "day": 1, "month": 13},
        headers=api_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 7. Event on non-existent contact
# ---------------------------------------------------------------------------


async def test_event_nonexistent_contact(client: AsyncClient, api_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/contacts/{fake_id}/events",
        json={"event_type": "birthday", "day": 1, "month": 1},
        headers=api_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. child_birthday with valid child_id
# ---------------------------------------------------------------------------


async def test_child_birthday_with_child_id(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)
    contact_id = contact["id"]

    # Create child first
    child_resp = await client.post(
        f"/api/contacts/{contact_id}/children",
        json={"name": "Sophie"},
        headers=api_headers,
    )
    assert child_resp.status_code == 201
    child_id = child_resp.json()["id"]

    # Create child_birthday event linked to child
    resp = await client.post(
        f"/api/contacts/{contact_id}/events",
        json={
            "event_type": "child_birthday",
            "day": 20,
            "month": 3,
            "year": 2018,
            "child_id": child_id,
        },
        headers=api_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["child_id"] == child_id
    assert data["event_type"] == "child_birthday"


# ---------------------------------------------------------------------------
# 9. Events cascade-deleted when contact is deleted
# ---------------------------------------------------------------------------


async def test_events_cascade_on_contact_delete(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers)
    contact_id = contact["id"]
    event = await create_test_event(client, api_headers, contact_id)

    # Delete contact
    resp = await client.delete(f"/api/contacts/{contact_id}", headers=api_headers)
    assert resp.status_code == 204

    # Event should be gone
    resp = await client.delete(f"/api/events/{event['id']}", headers=api_headers)
    assert resp.status_code == 404
