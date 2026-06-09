import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.models.contact import Contact
from src.schemas.contact import ContactCreate, ContactDetailResponse, ContactResponse, ContactUpdate

router = APIRouter()


@router.get("/contacts", response_model=list[ContactResponse])
async def list_contacts(
    visibility: str | None = Query(default=None, description="Filter by visibility: shared or personal"),
    db: AsyncSession = Depends(get_db),
):
    """List all contacts, ordered by name."""
    stmt = select(Contact).order_by(Contact.name)
    if visibility:
        stmt = stmt.where(Contact.visibility == visibility)
    result = await db.execute(stmt)
    contacts = result.scalars().all()
    return contacts


@router.get("/contacts/{contact_id}", response_model=ContactDetailResponse)
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single contact with all related events, children, and notes."""
    stmt = (
        select(Contact)
        .where(Contact.id == contact_id)
        .options(
            selectinload(Contact.events),
            selectinload(Contact.children),
            selectinload(Contact.notes),
        )
    )
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/contacts", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new contact."""
    contact = Contact(
        name=data.name,
        relationship_type=data.relationship_type,
        created_by=data.created_by,
        visibility=data.visibility,
    )
    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    return contact


@router.put("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a contact's fields."""
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    await db.flush()
    await db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a contact and all related data (cascade)."""
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.delete(contact)
    await db.flush()
