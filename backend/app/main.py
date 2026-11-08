import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.calendar import router as calendar_router
from app.api.catchup import router as catchup_router
from app.api.health import router as health_router
from app.api.media import router as media_router
from app.api.notifications import router as notifications_router
from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(media_router)
app.include_router(calendar_router)
app.include_router(catchup_router)
app.include_router(notifications_router)


@app.get("/api/v1", tags=["meta"])
def api_root() -> dict[str, str]:
    return {"name": "FRAME API", "version": "v1"}
