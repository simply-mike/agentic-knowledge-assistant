from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.config import get_settings
from app.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Agentic RAG assistant for enterprise knowledge bases.",
)

app.include_router(health_router)
