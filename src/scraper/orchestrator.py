"""
Scraper orchestrator — runs all sources in parallel,
deduplicates, and persists to database.
"""
import asyncio
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.config import config
from src.scraper.base import ScrapedJob
from src.scraper.adzuna import scrape_adzuna
from src.scraper.jsearch import scrape_jsearch
from src.scraper.remoteok import scrape_remoteok
from src.scraper.deduplicator import deduplicate_jobs
from src.db.models import Job, JobStatus, VisaStatus


async def harvest_jobs(db: AsyncSession) -> List[Job]:
    """
    Run all scrapers in parallel, deduplicate, filter new jobs,
    and persist to database. Returns list of new Job records.
    """
    logger.info("Starting job harvest...")

    # Run all scrapers concurrently
    results = await asyncio.gather(
        scrape_adzuna(),
        scrape_jsearch(),
        scrape_remoteok(),
        return_exceptions=True,
    )

    # Collect all jobs, handling any scraper failures gracefully
    all_scraped: List[ScrapedJob] = []
    source_names = ["Adzuna", "JSearch", "RemoteOK"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"{source_names[i]} scraper failed: {result}")
        elif isinstance(result, list):
            all_scraped.extend(result)

    logger.info(f"Raw scraped: {len(all_scraped)} jobs from all sources")

    # Deduplicate across sources
    unique_jobs = deduplicate_jobs(all_scraped)

    # Check which fingerprints already exist in DB
    fingerprints = [j.fingerprint for j in unique_jobs]
    if fingerprints:
        result = await db.execute(
            select(Job.fingerprint).where(Job.fingerprint.in_(fingerprints))
        )
        existing_fps = set(result.scalars().all())
    else:
        existing_fps = set()

    # Persist only new jobs
    new_jobs: List[Job] = []
    for scraped in unique_jobs:
        if scraped.fingerprint in existing_fps:
            continue

        job = Job(
            fingerprint=scraped.fingerprint,
            title=scraped.title,
            company=scraped.company,
            company_normalized=scraped.company_normalized,
            location=scraped.location,
            source=scraped.source,
            source_id=scraped.source_id,
            apply_url=scraped.apply_url,
            jd_text=scraped.jd_text,
            jd_html=scraped.jd_html,
            salary_min=scraped.salary_min,
            salary_max=scraped.salary_max,
            posted_date=scraped.posted_date,
            ats_platform=scraped.ats_platform or scraped.detect_ats_platform(),
            remote=scraped.remote,
            visa_status=VisaStatus.unchecked,
            status=JobStatus.scraped,
        )
        db.add(job)
        new_jobs.append(job)

    if new_jobs:
        await db.commit()

    logger.info(f"Harvest complete: {len(new_jobs)} new jobs added (skipped {len(existing_fps)} existing)")
    return new_jobs
