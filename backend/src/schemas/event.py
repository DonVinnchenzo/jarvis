import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class EventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    label: str | None = Field(default=None, max_length=200)
    child_id: uuid.UUID | None = None
    day: int = Field(..., ge=1, le=31)
    month: int = Field(..., ge=1, le=12)
    year: int | None = None
    recurring: bool = True

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        allowed = {"birthday", "anniversary", "child_birthday", "custom"}
        if v not in allowed:
            msg = f"event_type must be one of {allowed}"
            raise ValueError(msg)
        return v


class EventUpdate(BaseModel):
    event_type: str | None = Field(default=None, max_length=50)
    label: str | None = Field(default=None, max_length=200)
    child_id: uuid.UUID | None = None
    day: int | None = Field(default=None, ge=1, le=31)
    month: int | None = Field(default=None, ge=1, le=12)
    year: int | None = None
    recurring: bool | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"birthday", "anniversary", "child_birthday", "custom"}
        if v not in allowed:
            msg = f"event_type must be one of {allowed}"
            raise ValueError(msg)
        return v


class EventResponse(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    event_type: str
    label: str | None
    child_id: uuid.UUID | None
    day: int
    month: int
    year: int | None
    recurring: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
