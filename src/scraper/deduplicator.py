"""
Cross-source job deduplication.
Uses SHA256 fingerprints and URL matching.
"""
from typing import List, Set
from loguru import logger
from src.scraper.base import ScrapedJob


def deduplicate_jobs(jobs: List[ScrapedJob]) -> List[ScrapedJob]:
    """
    Remove duplicate jobs across all sources.
    Uses fingerprint (company+title+location) and apply_url.
    """
    seen_fingerprints: Set[str] = set()
    seen_urls: Set[str] = set()
    unique_jobs: List[ScrapedJob] = []

    for job in jobs:
        fp = job.fingerprint
        url = job.apply_url.split("?")[0].rstrip("/").lower()  # Normalize URL

        if fp in seen_fingerprints:
            continue
        if url in seen_urls:
            continue

        seen_fingerprints.add(fp)
        seen_urls.add(url)
        unique_jobs.append(job)

    removed = len(jobs) - len(unique_jobs)
    if removed > 0:
        logger.info(f"Deduplication: {len(jobs)} → {len(unique_jobs)} (removed {removed} duplicates)")

    return unique_jobs
