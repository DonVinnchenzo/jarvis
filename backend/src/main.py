from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import get_settings

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


@app.get("/api/health")
async def health():
    """Health check endpoint. No auth required."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
