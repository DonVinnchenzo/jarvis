from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.engine.reminder_engine import ReminderEngine
from src.models.reminder import ReminderConfig
from src.schemas.reminder import ReminderConfigCreate, ReminderConfigResponse, ReminderRunResponse

router = APIRouter()


@router.get("/reminders/config", response_model=list[ReminderConfigResponse])
async def list_reminder_configs(
    db: AsyncSession = Depends(get_db),
):
    """Get all global reminder configs (event_id IS NULL)."""
    stmt = (
        select(ReminderConfig)
        .where(ReminderConfig.event_id.is_(None))
        .order_by(ReminderConfig.days_before)
    )
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return configs


@router.post("/reminders/config", response_model=ReminderConfigResponse, status_code=201)
async def create_reminder_config(
    data: ReminderConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new global reminder config."""
    # Check if a config with the same days_before already exists
    stmt = select(ReminderConfig).where(
        ReminderConfig.event_id.is_(None),
        ReminderConfig.days_before == data.days_before,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing config
        existing.enabled = data.enabled
        await db.flush()
        await db.refresh(existing)
        return existing

    config = ReminderConfig(
        event_id=None,
        days_before=data.days_before,
        enabled=data.enabled,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


@router.post("/reminders/run", response_model=ReminderRunResponse)
async def run_reminders(
    db: AsyncSession = Depends(get_db),
):
    """Trigger the reminder engine. Called by cron daily at 08:00."""
    settings = get_settings()
    engine = ReminderEngine(db, settings)
    result = await engine.run()
    return result
