from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.routes import briefing, children, contacts, events, health, notes, reminders, search, upcoming

app = FastAPI(title="Jarvis API", version="0.1.0")


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Check X-API-Key header on all /api/* routes except /api/health."""
    path = request.url.path

    # Skip auth for health check, docs, and openapi spec
    exempt_paths = ["/api/health", "/docs", "/openapi.json", "/redoc"]
    if any(path.startswith(p) for p in exempt_paths):
        return await call_next(request)

    # Require API key for all other /api/* routes
    if path.startswith("/api/"):
        settings = get_settings()
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != settings.JARVIS_API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

    return await call_next(request)


# Wire all routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(contacts.router, prefix="/api", tags=["contacts"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(children.router, prefix="/api", tags=["children"])
app.include_router(notes.router, prefix="/api", tags=["notes"])
app.include_router(upcoming.router, prefix="/api", tags=["upcoming"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(reminders.router, prefix="/api", tags=["reminders"])
app.include_router(briefing.router, prefix="/api", tags=["briefing"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
