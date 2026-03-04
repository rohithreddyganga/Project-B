"""
Freshness-based priority sorting.
Jobs < 4 hours old get boosted, > 14 days get deprioritized.
"""
from datetime import datetime, timezone, timedelta
from typing import List

from loguru import logger
from src.config import config
from src.db.models import Job


def sort_by_freshness_and_score(jobs: List[Job]) -> List[Job]:
    """
    Sort jobs by priority: freshness-boosted score.
    Priority = match_score * freshness_multiplier
    """
    rules = config.rules
    boost_hours = rules.get("freshness_boost_hours", 4)
    boost_mult = rules.get("freshness_boost_multiplier", 1.3)
    stale_days = rules.get("stale_deprioritize_days", 14)
    stale_mult = rules.get("stale_deprioritize_multiplier", 0.7)

    now = datetime.now(timezone.utc)

    def priority_key(job: Job) -> float:
        base_score = job.match_score or 0.0

        if job.posted_date:
            age = now - job.posted_date
            if age < timedelta(hours=boost_hours):
                return base_score * boost_mult
            elif age > timedelta(days=stale_days):
                return base_score * stale_mult

        return base_score

    sorted_jobs = sorted(jobs, key=priority_key, reverse=True)
    logger.info(f"Sorted {len(sorted_jobs)} jobs by freshness-weighted score")
    return sorted_jobs
