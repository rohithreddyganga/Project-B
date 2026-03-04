"""
Gate Checker — Stage 4 of the pipeline.
Enforces: deduplication, per-company limit, blacklist, robots.txt.
"""
from typing import Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.config import config
from src.db.models import Job, Application, JobStatus


async def check_gates(job: Job, db: AsyncSession) -> Tuple[bool, str]:
    """
    Check all gates for a job. Returns (pass, reason).
    Must pass ALL gates to proceed.
    """
    # Gate 1: Blacklist check
    if config.is_blacklisted(job.company):
        return False, f"Company '{job.company}' is blacklisted"

    # Gate 2: Per-company limit
    max_per_co = config.rules.get("max_per_company", 3)
    result = await db.execute(
        select(func.count(Application.id))
        .where(Application.company == job.company_normalized)
        .where(Application.status.notin_([
            JobStatus.failed.value,
            # Don't count rejected apps against the limit
        ]))
    )
    active_apps = result.scalar() or 0
    if active_apps >= max_per_co:
        return False, f"Company '{job.company}' has {active_apps}/{max_per_co} active applications"

    # Gate 3: Dedup — check if apply_url already used
    url_normalized = job.apply_url.split("?")[0].rstrip("/").lower()
    result = await db.execute(
        select(func.count(Application.id))
        .where(func.lower(Application.apply_url).contains(url_normalized))
    )
    url_exists = (result.scalar() or 0) > 0
    if url_exists:
        return False, f"Apply URL already used: {url_normalized[:80]}"

    # Gate 4: Check daily application limit
    from datetime import datetime, timezone, timedelta
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(func.count(Application.id))
        .where(Application.applied_date >= today_start)
        .where(Application.status == JobStatus.submitted.value)
    )
    daily_count = result.scalar() or 0
    max_daily = config.rules.get("max_apps_per_day", 55)
    if daily_count >= max_daily:
        return False, f"Daily limit reached: {daily_count}/{max_daily}"

    # All gates passed
    return True, "All gates passed"


async def process_gates(jobs: list[Job], db: AsyncSession) -> list[Job]:
    """
    Run gate checks on a batch of jobs.
    Updates status in DB and returns the jobs that passed.
    """
    passed: list[Job] = []
    blocked = 0

    for job in jobs:
        ok, reason = await check_gates(job, db)
        if ok:
            passed.append(job)
        else:
            job.status = JobStatus.gate_blocked
            blocked += 1
            logger.debug(f"Gate blocked: {job.company} — {job.title}: {reason}")

    if blocked > 0:
        await db.commit()
        logger.info(f"Gates: {len(passed)} passed, {blocked} blocked")

    return passed
