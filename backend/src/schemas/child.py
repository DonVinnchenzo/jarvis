import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChildCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ChildUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)


class ChildResponse(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
