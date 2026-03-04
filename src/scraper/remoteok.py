"""
RemoteOK API scraper.
Completely free, no API key needed. Returns JSON.
"""
import httpx
from datetime import datetime, timezone
from typing import List

from loguru import logger
from src.config import config
from src.scraper.base import ScrapedJob


REMOTEOK_URL = "https://remoteok.com/api"


async def scrape_remoteok(max_results: int = 100) -> List[ScrapedJob]:
    """Scrape remote tech jobs from RemoteOK."""
    source_cfg = config.sources.get("remoteok", {})
    if not source_cfg.get("enabled", True):
        return []

    target_titles = [t.lower() for t in config.job_criteria.get("titles", [])]
    exclude_kw = [k.lower() for k in config.job_criteria.get("exclude_keywords", [])]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(REMOTEOK_URL, headers={
                "User-Agent": "AutoApply Job Agent/2.0 (personal use)"
            })
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"RemoteOK API error: {e}")
        return []

    # First item is metadata, skip it
    if data and isinstance(data[0], dict) and "legal" in str(data[0]):
        data = data[1:]

    jobs: List[ScrapedJob] = []
    for r in data:
        if len(jobs) >= max_results:
            break

        title = r.get("position", "")
        company = r.get("company", "Unknown")

        # Filter by target titles
        title_lower = title.lower()
        if target_titles and not any(t in title_lower for t in target_titles):
            continue

        # Exclude senior/principal etc.
        if any(ex in title_lower for ex in exclude_kw):
            continue

        # Parse date
        posted = None
        if r.get("date"):
            try:
                posted = datetime.fromisoformat(
                    r["date"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        slug = r.get("slug", r.get("id", ""))

        job = ScrapedJob(
            title=title,
            company=company,
            location="Remote",
            source="remoteok",
            source_id=str(r.get("id", "")),
            apply_url=r.get("url", f"https://remoteok.com/l/{slug}"),
            jd_text=r.get("description", ""),
            salary_min=_parse_salary(r.get("salary_min")),
            salary_max=_parse_salary(r.get("salary_max")),
            posted_date=posted,
            remote=True,
        )
        job.ats_platform = job.detect_ats_platform()
        jobs.append(job)

    logger.info(f"RemoteOK: scraped {len(jobs)} matching jobs")
    return jobs


def _parse_salary(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").replace("$", "").replace("k", "000"))
    except (ValueError, TypeError):
        return None
