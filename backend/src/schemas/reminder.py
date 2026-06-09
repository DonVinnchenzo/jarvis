import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReminderConfigCreate(BaseModel):
    days_before: int = Field(..., ge=0)
    enabled: bool = True


class ReminderConfigResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID | None
    days_before: int
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReminderRunResponse(BaseModel):
    status: str
    reminders_sent: int = 0
    reminders_skipped: int = 0
    total_events: int = 0
    errors: list[str] = []
