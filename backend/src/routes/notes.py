import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.contact import Contact
from src.models.note import ContactNote
from src.schemas.note import NoteCreate, NoteResponse

router = APIRouter()


@router.post("/contacts/{contact_id}/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    contact_id: uuid.UUID,
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a note to a contact."""
    # Verify contact exists
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    note = ContactNote(
        contact_id=contact_id,
        note_text=data.note_text,
        created_by=data.created_by,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


@router.get("/contacts/{contact_id}/notes", response_model=list[NoteResponse])
async def list_notes(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all notes for a contact, newest first."""
    # Verify contact exists
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    stmt = (
        select(ContactNote)
        .where(ContactNote.contact_id == contact_id)
        .order_by(ContactNote.created_at.desc())
    )
    result = await db.execute(stmt)
    notes = result.scalars().all()
    return notes


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a note."""
    stmt = select(ContactNote).where(ContactNote.id == note_id)
    result = await db.execute(stmt)
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    await db.delete(note)
    await db.flush()
