"""Tests for the contacts CRUD endpoints.

8 tests: list, create, get detail, update, delete, cascade delete,
validation (empty name), and auth (missing API key).
"""

from httpx import AsyncClient

from tests.conftest import create_test_contact, create_test_event

# ---------------------------------------------------------------------------
# 1. Create a contact
# ---------------------------------------------------------------------------


async def test_create_contact(client: AsyncClient, api_headers: dict):
    resp = await client.post(
        "/api/contacts",
        json={
            "name": "Lisa Jansen",
            "relationship_type": "colleague",
            "created_by": "vincent",
        },
        headers=api_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Lisa Jansen"
    assert data["relationship_type"] == "colleague"
    assert data["visibility"] == "shared"
    assert data["created_by"] == "vincent"
    assert "id" in data


# ---------------------------------------------------------------------------
# 2. List contacts
# ---------------------------------------------------------------------------


async def test_list_contacts(client: AsyncClient, api_headers: dict):
    await create_test_contact(client, api_headers, name="Alice")
    await create_test_contact(client, api_headers, name="Bob")

    resp = await client.get("/api/contacts", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Sorted by name
    assert data[0]["name"] == "Alice"
    assert data[1]["name"] == "Bob"


# ---------------------------------------------------------------------------
# 3. Get contact detail (with events, children, notes)
# ---------------------------------------------------------------------------


async def test_get_contact_detail(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Mark de Vries")
    contact_id = contact["id"]

    # Add an event
    await create_test_event(client, api_headers, contact_id)

    # Add a note
    await client.post(
        f"/api/contacts/{contact_id}/notes",
        json={"note_text": "Just got promoted", "created_by": "vincent"},
        headers=api_headers,
    )

    # Add a child
    await client.post(
        f"/api/contacts/{contact_id}/children",
        json={"name": "Sophie"},
        headers=api_headers,
    )

    resp = await client.get(f"/api/contacts/{contact_id}", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Mark de Vries"
    assert len(data["events"]) == 1
    assert len(data["notes"]) == 1
    assert len(data["children"]) == 1
    assert data["children"][0]["name"] == "Sophie"


# ---------------------------------------------------------------------------
# 4. Update a contact
# ---------------------------------------------------------------------------


async def test_update_contact(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Old Name")
    contact_id = contact["id"]

    resp = await client.put(
        f"/api/contacts/{contact_id}",
        json={"name": "New Name", "relationship_type": "family"},
        headers=api_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["relationship_type"] == "family"


# ---------------------------------------------------------------------------
# 5. Delete a contact
# ---------------------------------------------------------------------------


async def test_delete_contact(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="To Delete")
    contact_id = contact["id"]

    resp = await client.delete(f"/api/contacts/{contact_id}", headers=api_headers)
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"/api/contacts/{contact_id}", headers=api_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Cascade delete — deleting contact removes events, children, notes
# ---------------------------------------------------------------------------


async def test_cascade_delete_removes_related(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Cascade Test")
    contact_id = contact["id"]

    # Create related records
    event = await create_test_event(client, api_headers, contact_id)
    await client.post(
        f"/api/contacts/{contact_id}/notes",
        json={"note_text": "Will be deleted", "created_by": "vincent"},
        headers=api_headers,
    )
    await client.post(
        f"/api/contacts/{contact_id}/children",
        json={"name": "ChildToDelete"},
        headers=api_headers,
    )

    # Delete the contact
    resp = await client.delete(f"/api/contacts/{contact_id}", headers=api_headers)
    assert resp.status_code == 204

    # Event should be gone (via its own endpoint, if it existed)
    # We verify by trying to get the contact detail — should be 404
    resp = await client.get(f"/api/contacts/{contact_id}", headers=api_headers)
    assert resp.status_code == 404

    # Also verify event is gone by trying to delete it
    resp = await client.delete(f"/api/events/{event['id']}", headers=api_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7. Validation — empty name should fail
# ---------------------------------------------------------------------------


async def test_create_contact_empty_name_fails(client: AsyncClient, api_headers: dict):
    resp = await client.post(
        "/api/contacts",
        json={
            "name": "",
            "relationship_type": "friend",
            "created_by": "vincent",
        },
        headers=api_headers,
    )
    assert resp.status_code == 422  # Pydantic validation error


# ---------------------------------------------------------------------------
# 8. Auth — missing API key returns 401
# ---------------------------------------------------------------------------


async def test_missing_api_key_returns_401(client: AsyncClient):
    resp = await client.get("/api/contacts")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or missing API key"
