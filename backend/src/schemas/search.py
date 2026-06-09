import uuid

from pydantic import BaseModel


class SearchResult(BaseModel):
    contact_id: uuid.UUID
    contact_name: str
    match_type: str  # "name", "note", "child", "relationship"
    match_text: str

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
