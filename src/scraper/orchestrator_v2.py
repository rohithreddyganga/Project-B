"""
Scraper orchestrator — runs ALL sources in parallel,
deduplicates, and persists to database.

Full-scale: 9 sources (3 API + 3 RapidAPI + 3 ATS feeds).
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
from src.scraper.linkedin_api import scrape_linkedin_api
from src.scraper.activejobs import scrape_activejobs
from src.scraper.jobs_search_api import scrape_jobs_search_api
from src.scraper.ats_feeds import scrape_greenhouse, scrape_lever, scrape_smartrecruiters
from src.scraper.deduplicator import deduplicate_jobs
from src.db.models import Job, JobStatus, VisaStatus


async def harvest_jobs(db: AsyncSession) -> List[Job]:
    """
    Run all scrapers in parallel, deduplicate, filter new jobs,
    and persist to database. Returns list of new Job records.

    9 sources:
      - Adzuna (API key)
      - JSearch / RapidAPI (API key)
      - RemoteOK (free)
      - LinkedIn API / RapidAPI (API key — same as JSearch)
      - Active Jobs DB / RapidAPI (API key — same as JSearch)
      - Jobs Search API / RapidAPI (API key — same as JSearch)
      - Greenhouse (free — public board API)
      - Lever (free — public postings API)
      - SmartRecruiters (free — public API)
    """
    logger.info("Starting job harvest (9 sources — full scale)...")

    # Run all scrapers concurrently
    results = await asyncio.gather(
        scrape_adzuna(),
        scrape_jsearch(),
        scrape_remoteok(),
        scrape_linkedin_api(),
        scrape_activejobs(),
        scrape_jobs_search_api(),
        scrape_greenhouse(),
        scrape_lever(),
        scrape_smartrecruiters(),
        return_exceptions=True,
    )

    # Collect all jobs, handling any scraper failures gracefully
    all_scraped: List[ScrapedJob] = []
    source_names = [
        "Adzuna", "JSearch", "RemoteOK",
        "LinkedIn API", "Active Jobs DB", "Jobs Search API",
        "Greenhouse", "Lever", "SmartRecruiters",
    ]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"{source_names[i]} scraper failed: {result}")
        elif isinstance(result, list):
            logger.info(f"  {source_names[i]}: {len(result)} jobs")
            all_scraped.extend(result)

    logger.info(f"Raw scraped: {len(all_scraped)} jobs from all sources")

    # Deduplicate across sources
    unique_jobs = deduplicate_jobs(all_scraped)

    # Check which fingerprints already exist in DB
    fingerprints = [j.fingerprint for j in unique_jobs]
    if fingerprints:
        # Batch check in chunks of 500 to avoid SQLite limits
        existing_fps = set()
        for i in range(0, len(fingerprints), 500):
            chunk = fingerprints[i:i + 500]
            result = await db.execute(
                select(Job.fingerprint).where(Job.fingerprint.in_(chunk))
            )
            existing_fps.update(result.scalars().all())
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

    logger.info(
        f"Harvest complete: {len(new_jobs)} new jobs added "
        f"(skipped {len(existing_fps)} existing, "
        f"{len(all_scraped) - len(unique_jobs)} cross-source duplicates)"
    )
    return new_jobs
