"""Pydantic schemas for the briefing module."""

from pydantic import BaseModel


class BriefingRunResponse(BaseModel):
    status: str
    sent: int = 0
    weather_available: bool = False
    divvy_available: bool = False
    todays_events: int = 0
    errors: list[str] = []
