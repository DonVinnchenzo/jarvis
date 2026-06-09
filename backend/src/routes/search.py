from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.child import ContactChild
from src.models.contact import Contact
from src.models.note import ContactNote
from src.schemas.search import SearchResponse, SearchResult

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search term"),
    db: AsyncSession = Depends(get_db),
):
    """Search contacts, notes, and children using ILIKE."""
    term = f"%{q.strip()}%"
    results: list[SearchResult] = []
    seen_contacts: set[str] = set()  # Track unique (contact_id, match_type, match_text)

    # 1. Search by contact name
    stmt = select(Contact).where(Contact.name.ilike(term)).order_by(Contact.name)
    result = await db.execute(stmt)
    for contact in result.scalars().all():
        key = f"{contact.id}:name:{contact.name}"
        if key not in seen_contacts:
            seen_contacts.add(key)
            results.append(
                SearchResult(
                    contact_id=contact.id,
                    contact_name=contact.name,
                    match_type="name",
                    match_text=contact.name,
                )
            )

    # 2. Search by relationship type
    stmt = select(Contact).where(Contact.relationship_type.ilike(term)).order_by(Contact.name)
    result = await db.execute(stmt)
    for contact in result.scalars().all():
        key = f"{contact.id}:relationship:{contact.relationship_type}"
        if key not in seen_contacts:
            seen_contacts.add(key)
            results.append(
                SearchResult(
                    contact_id=contact.id,
                    contact_name=contact.name,
                    match_type="relationship",
                    match_text=contact.relationship_type,
                )
            )

    # 3. Search by note text
    stmt = (
        select(ContactNote, Contact)
        .join(Contact, ContactNote.contact_id == Contact.id)
        .where(ContactNote.note_text.ilike(term))
        .order_by(ContactNote.created_at.desc())
    )
    result = await db.execute(stmt)
    for note, contact in result.all():
        key = f"{contact.id}:note:{note.note_text}"
        if key not in seen_contacts:
            seen_contacts.add(key)
            results.append(
                SearchResult(
                    contact_id=contact.id,
                    contact_name=contact.name,
                    match_type="note",
                    match_text=note.note_text,
                )
            )

    # 4. Search by child name
    stmt = (
        select(ContactChild, Contact)
        .join(Contact, ContactChild.contact_id == Contact.id)
        .where(ContactChild.name.ilike(term))
        .order_by(ContactChild.name)
    )
    result = await db.execute(stmt)
    for child, contact in result.all():
        key = f"{contact.id}:child:{child.name}"
        if key not in seen_contacts:
            seen_contacts.add(key)
            results.append(
                SearchResult(
                    contact_id=contact.id,
                    contact_name=contact.name,
                    match_type="child",
                    match_text=child.name,
                )
            )

    return SearchResponse(results=results, total=len(results))
