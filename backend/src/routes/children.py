import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.child import ContactChild
from src.models.contact import Contact
from src.schemas.child import ChildCreate, ChildResponse, ChildUpdate

router = APIRouter()


@router.post("/contacts/{contact_id}/children", response_model=ChildResponse, status_code=201)
async def create_child(
    contact_id: uuid.UUID,
    data: ChildCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a child to a contact."""
    # Verify contact exists
    stmt = select(Contact).where(Contact.id == contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    child = ContactChild(
        contact_id=contact_id,
        name=data.name,
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)
    return child


@router.put("/children/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: uuid.UUID,
    data: ChildUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a child's name."""
    stmt = select(ContactChild).where(ContactChild.id == child_id)
    result = await db.execute(stmt)
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(child, field, value)

    await db.flush()
    await db.refresh(child)
    return child


@router.delete("/children/{child_id}", status_code=204)
async def delete_child(
    child_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a child (cascade deletes linked events)."""
    stmt = select(ContactChild).where(ContactChild.id == child_id)
    result = await db.execute(stmt)
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")

    await db.delete(child)
    await db.flush()
