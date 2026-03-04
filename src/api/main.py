"""
FastAPI application — backend for the AutoApply Dashboard.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from src.config import config
from src.db.session import init_db
from src.api.routes.jobs import router as jobs_router
from src.api.routes.applications import router as apps_router
from src.api.routes.resume import router as resume_router
from src.api.routes.stats import router as stats_router
from src.api.routes.settings_routes import router as settings_router
from src.pipeline.scheduler import run_daily_pipeline


scheduler = AsyncIOScheduler(timezone=config.schedule.get("timezone", "US/Eastern"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await init_db()
    logger.info("Database initialized")

    # Schedule daily pipeline
    harvest_time = config.schedule.get("harvest_time", "06:00")
    hour, minute = map(int, harvest_time.split(":"))
    scheduler.add_job(
        run_daily_pipeline,
        "cron",
        hour=hour,
        minute=minute,
        id="daily_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — daily pipeline at {harvest_time}")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="AutoApply Agent API",
    version="2.0.0",
    description="Backend for the autonomous job application system",
    lifespan=lifespan,
)

# CORS for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(apps_router, prefix="/api/applications", tags=["Applications"])
app.include_router(resume_router, prefix="/api/resume", tags=["Resume"])
app.include_router(stats_router, prefix="/api/stats", tags=["Statistics"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/pipeline/trigger")
async def trigger_pipeline():
    """Manually trigger the daily pipeline."""
    asyncio.create_task(run_daily_pipeline())
    return {"status": "Pipeline triggered", "message": "Running in background"}
