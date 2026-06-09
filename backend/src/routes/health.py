from fastapi import APIRouter

from src.engine.heartbeat import read_heartbeat

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint. No auth required."""
    last_run = read_heartbeat()
    return {
        "status": "ok",
        "last_successful_reminder_run": last_run.isoformat() if last_run else None,
    }
