import uuid

from pydantic import BaseModel


class UpcomingEvent(BaseModel):
    contact_name: str
    contact_id: uuid.UUID
    event_type: str
    label: str | None
    day: int
    month: int
    year: int | None
    days_until: int
    date_display: str
    age: int | None = None

    model_config = {"from_attributes": True}


class UpcomingResponse(BaseModel):
    events: list[UpcomingEvent]
    total: int
