"""
Entry point for running the AutoApply Agent.
Can run just the API, just the pipeline, or both.
"""
import sys
import asyncio
import logging
import uvicorn
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan> — {message}",
    level="INFO",
)
logger.add(
    "logs/autoapply_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="14 days",
    level="DEBUG",
)

# Suppress verbose SQLAlchemy SQL query logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def main():
    import os
    os.makedirs("logs", exist_ok=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else "serve"

    if mode == "serve":
        # Run the API server (scheduler runs inside)
        logger.info("Starting AutoApply Agent API server...")
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
        )

    elif mode == "pipeline":
        # Run the pipeline once (for testing)
        logger.info("Running pipeline manually...")
        from src.pipeline.scheduler import run_daily_pipeline
        asyncio.run(run_daily_pipeline())

    elif mode == "scrape":
        # Just scrape jobs (for testing)
        logger.info("Running scraper only...")
        from src.db.session import async_session, init_db
        from src.scraper.orchestrator_v2 import harvest_jobs

        async def _scrape():
            await init_db()
            async with async_session() as db:
                jobs = await harvest_jobs(db)
                logger.info(f"Scraped {len(jobs)} new jobs")

        asyncio.run(_scrape())

    else:
        print(f"Usage: python run.py [serve|pipeline|scrape]")
        sys.exit(1)


if __name__ == "__main__":
    main()
