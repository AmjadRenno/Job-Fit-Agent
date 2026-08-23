import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.best_match import router as best_match_router
from app.api.routes.cover_letter import router as cover_letter_router
from app.api.routes.health import router as health_router
from app.api.routes.job_analysis import router as job_analysis_router
from app.config import get_settings
from app.infrastructure.logging.setup import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(job_analysis_router)
app.include_router(best_match_router)
app.include_router(cover_letter_router)

logger.info("Application started in %s environment", settings.app_environment)
