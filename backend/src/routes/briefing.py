"""Morning Briefing API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.briefing.engine import BriefingEngine
from src.briefing.schemas import BriefingRunResponse
from src.config import get_settings
from src.database import get_db

router = APIRouter()


@router.post("/briefing/run", response_model=BriefingRunResponse)
async def run_briefing(
    db: AsyncSession = Depends(get_db),
):
    """Trigger morning briefing for all users. Called by cron at 07:00 CT."""
    settings = get_settings()
    engine = BriefingEngine(db, settings)
    result = await engine.run()
    return result


@router.get("/briefing")
async def get_briefing(
    user_name: str = Query(..., description="User display name (Vincent or Christianne)"),
    db: AsyncSession = Depends(get_db),
):
    """Generate on-demand briefing for a specific user. Returns the message text."""
    settings = get_settings()
    engine = BriefingEngine(db, settings)
    message = await engine.get_briefing_for_user(user_name)
    return {"message": message}


@router.get("/briefing/bikes")
async def get_bikes():
    """Get current Divvy status for all tracked stations."""
    message = await BriefingEngine.get_bikes_status()
    return {"message": message}


@router.get("/briefing/weather")
async def get_weather():
    """Get current weather data."""
    message = await BriefingEngine.get_weather_status()
    return {"message": message}
