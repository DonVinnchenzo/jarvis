"""Tests for the /api/search endpoint.

7 tests: search by name, partial match, notes, children, relationship type,
no results, and multi-match (same contact matched by multiple criteria).
"""

from httpx import AsyncClient

from tests.conftest import create_test_contact

# ---------------------------------------------------------------------------
# 1. Search by contact name
# ---------------------------------------------------------------------------


async def test_search_by_name(client: AsyncClient, api_headers: dict):
    await create_test_contact(client, api_headers, name="Mark de Vries")

    resp = await client.get("/api/search?q=Mark", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(r["match_type"] == "name" and "Mark" in r["match_text"] for r in data["results"])


# ---------------------------------------------------------------------------
# 2. Partial match
# ---------------------------------------------------------------------------


async def test_search_partial_match(client: AsyncClient, api_headers: dict):
    await create_test_contact(client, api_headers, name="Lisa Jansen")

    resp = await client.get("/api/search?q=jan", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(r["contact_name"] == "Lisa Jansen" for r in data["results"])


# ---------------------------------------------------------------------------
# 3. Search by note text
# ---------------------------------------------------------------------------


async def test_search_by_note(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Bob")
    contact_id = contact["id"]

    await client.post(
        f"/api/contacts/{contact_id}/notes",
        json={"note_text": "Got promoted to senior manager", "created_by": "vincent"},
        headers=api_headers,
    )

    resp = await client.get("/api/search?q=promoted", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    note_results = [r for r in data["results"] if r["match_type"] == "note"]
    assert len(note_results) >= 1
    assert note_results[0]["contact_name"] == "Bob"


# ---------------------------------------------------------------------------
# 4. Search by child name
# ---------------------------------------------------------------------------


async def test_search_by_child(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Alice")
    contact_id = contact["id"]

    await client.post(
        f"/api/contacts/{contact_id}/children",
        json={"name": "Sophie"},
        headers=api_headers,
    )

    resp = await client.get("/api/search?q=Sophie", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    child_results = [r for r in data["results"] if r["match_type"] == "child"]
    assert len(child_results) >= 1
    assert child_results[0]["contact_name"] == "Alice"


# ---------------------------------------------------------------------------
# 5. Search by relationship type
# ---------------------------------------------------------------------------


async def test_search_by_relationship(client: AsyncClient, api_headers: dict):
    await create_test_contact(client, api_headers, name="Tom", relationship_type="colleague")

    resp = await client.get("/api/search?q=colleague", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    rel_results = [r for r in data["results"] if r["match_type"] == "relationship"]
    assert len(rel_results) >= 1
    assert rel_results[0]["contact_name"] == "Tom"


# ---------------------------------------------------------------------------
# 6. No results
# ---------------------------------------------------------------------------


async def test_search_no_results(client: AsyncClient, api_headers: dict):
    await create_test_contact(client, api_headers, name="Mark")

    resp = await client.get("/api/search?q=zzzznonexistent", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["results"] == []


# ---------------------------------------------------------------------------
# 7. Multi-match: same contact found via name AND note
# ---------------------------------------------------------------------------


async def test_search_multi_match(client: AsyncClient, api_headers: dict):
    contact = await create_test_contact(client, api_headers, name="Vincent")
    contact_id = contact["id"]

    await client.post(
        f"/api/contacts/{contact_id}/notes",
        json={"note_text": "Vincent loves cycling", "created_by": "christianne"},
        headers=api_headers,
    )

    resp = await client.get("/api/search?q=Vincent", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Should have at least 2 results: one name match, one note match
    assert data["total"] >= 2
    match_types = {r["match_type"] for r in data["results"]}
    assert "name" in match_types
    assert "note" in match_types
