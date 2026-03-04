"""
Scraper Manager — orchestrates all job sources.
Runs all scrapers in parallel, normalizes, deduplicates.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.config import config
from src.db.database import get_async_session
from src.db.models import Application, ApplicationStatus, JobSource
from src.scraper import adzuna, jsearch, remoteok
from src.scraper.deduplicator import compute_fingerprint

logger = logging.getLogger(__name__)


async def run_scrape_cycle() -> dict:
    """
    Execute a full scrape cycle across all sources.
    Returns stats dict.
    """
    stats = {"total_scraped": 0, "new_jobs": 0, "duplicates": 0, "errors": 0}

    # Run all scrapers in parallel
    logger.info("Starting scrape cycle...")
    results = await asyncio.gather(
        _safe_scrape("adzuna", adzuna.scrape),
        _safe_scrape("jsearch", jsearch.scrape),
        _safe_scrape("remoteok", remoteok.scrape),
        return_exceptions=True,
    )

    # Flatten results
    all_jobs = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Scraper error: {result}")
            stats["errors"] += 1
            continue
        all_jobs.extend(result)

    stats["total_scraped"] = len(all_jobs)
    logger.info(f"Total raw jobs scraped: {len(all_jobs)}")

    # Filter by age
    cutoff = datetime.utcnow() - timedelta(days=config.search.max_job_age_days)
    fresh_jobs = []
    for job in all_jobs:
        posted = job.get("posted_date")
        if posted and posted < cutoff:
            continue
        fresh_jobs.append(job)

    # Add fingerprints
    for job in fresh_jobs:
        job["job_fingerprint"] = compute_fingerprint(
            job.get("company", ""),
            job.get("title", ""),
            job.get("location", ""),
        )

    # Deduplicate in-memory (cross-source)
    seen = set()
    unique_jobs = []
    for job in fresh_jobs:
        fp = job["job_fingerprint"]
        if fp not in seen:
            seen.add(fp)
            unique_jobs.append(job)
        else:
            stats["duplicates"] += 1

    # Insert into DB (skip existing)
    async with get_async_session() as session:
        for job in unique_jobs:
            # Check if fingerprint already exists
            existing = await session.execute(
                select(Application.id).where(
                    Application.job_fingerprint == job["job_fingerprint"]
                )
            )
            if existing.scalar():
                stats["duplicates"] += 1
                continue

            app = Application(
                job_fingerprint=job["job_fingerprint"],
                title=job.get("title", "")[:300],
                company=job.get("company", "Unknown")[:200],
                location=job.get("location"),
                salary_min=job.get("salary_min"),
                salary_max=job.get("salary_max"),
                job_type=job.get("job_type"),
                remote=job.get("remote", False),
                source=job.get("source", JobSource.MANUAL),
                source_job_id=str(job.get("source_job_id", "")),
                apply_url=job.get("apply_url", ""),
                company_url=job.get("company_url"),
                jd_text=job.get("jd_text", ""),
                posted_date=job.get("posted_date"),
                status=ApplicationStatus.SCRAPED,
            )
            session.add(app)
            stats["new_jobs"] += 1

        await session.commit()

    logger.info(
        f"Scrape complete: {stats['total_scraped']} scraped, "
        f"{stats['new_jobs']} new, {stats['duplicates']} dupes"
    )
    return stats


async def _safe_scrape(name: str, scrape_fn) -> list[dict]:
    """Wrap a scraper in error handling."""
    try:
        return await scrape_fn()
    except Exception as e:
        logger.error(f"Scraper '{name}' failed: {e}")
        return []
