import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.child import ChildResponse
from src.schemas.event import EventResponse
from src.schemas.note import NoteResponse


class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    relationship_type: str = Field(..., min_length=1, max_length=100)
    created_by: str = Field(..., min_length=1, max_length=50)
    visibility: str = Field(default="shared", max_length=20)


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    relationship_type: str | None = Field(default=None, min_length=1, max_length=100)
    visibility: str | None = Field(default=None, max_length=20)


class ContactResponse(BaseModel):
    id: uuid.UUID
    name: str
    relationship_type: str
    visibility: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactDetailResponse(ContactResponse):
    events: list[EventResponse] = []
    children: list[ChildResponse] = []
    notes: list[NoteResponse] = []
