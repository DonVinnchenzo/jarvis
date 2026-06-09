import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.child import ContactChild
from src.models.contact import Contact
from src.models.event import ContactEvent
from src.schemas.event import EventCreate, EventResponse, EventUpdate

router = APIRouter()


@router.post("/contacts/{contact_id}/events", response_model=EventResponse, status_code=201)
async def create_event(
    contact_id: uuid.UUID,
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add an event to a contact."""
    # Verify contact exists
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # If child_birthday with child_id, verify child belongs to same contact
    if data.event_type == "child_birthday" and data.child_id:
        stmt = select(ContactChild).where(
            ContactChild.id == data.child_id,
            ContactChild.contact_id == contact_id,
        )
        result = await db.execute(stmt)
        child = result.scalar_one_or_none()
        if not child:
            raise HTTPException(
                status_code=400,
                detail="Child not found or does not belong to this contact",
            )

    event = ContactEvent(
        contact_id=contact_id,
        event_type=data.event_type,
        label=data.label,
        child_id=data.child_id,
        day=data.day,
        month=data.month,
        year=data.year,
        recurring=data.recurring,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an event."""
    stmt = select(ContactEvent).where(ContactEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    await db.flush()
    await db.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete an event."""
    stmt = select(ContactEvent).where(ContactEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.delete(event)
    await db.flush()
