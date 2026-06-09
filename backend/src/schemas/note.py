import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    note_text: str = Field(..., min_length=1)
    created_by: str = Field(..., min_length=1, max_length=50)


class NoteResponse(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    note_text: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
