"""
JSearch API scraper (via RapidAPI).
Free tier: 200 requests/day.
Aggregates Indeed, Glassdoor, LinkedIn, ZipRecruiter, etc. — legally.
"""
import httpx
from datetime import datetime, timezone
from typing import List

from loguru import logger
from src.config import config
from src.scraper.base import ScrapedJob


JSEARCH_BASE = "https://jsearch.p.rapidapi.com/search"


async def scrape_jsearch(
    titles: List[str] | None = None,
    location: str = "United States",
    max_results: int = 150,
) -> List[ScrapedJob]:
    """
    Scrape jobs from JSearch API.
    This legally aggregates Indeed, Glassdoor, LinkedIn, and other boards.
    """
    api_key = config.env.jsearch_api_key
    if not api_key:
        logger.warning("JSearch API key not configured, skipping")
        return []

    source_cfg = config.sources.get("jsearch", {})
    if not source_cfg.get("enabled", True):
        return []

    per_page = source_cfg.get("results_per_page", 20)
    max_pages = source_cfg.get("max_pages", 10)
    search_titles = titles or config.job_criteria.get("titles", ["Software Engineer"])

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    all_jobs: List[ScrapedJob] = []
    seen_ids: set = set()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for title in search_titles:
            for page in range(1, max_pages + 1):
                if len(all_jobs) >= max_results:
                    break

                params = {
                    "query": f"{title} in {location}",
                    "page": str(page),
                    "num_pages": "1",
                    "date_posted": "week",         # Last 7 days
                    "remote_jobs_only": "false",
                }

                try:
                    resp = await client.get(JSEARCH_BASE, headers=headers, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as e:
                    logger.error(f"JSearch API error (title={title}, page={page}): {e}")
                    break

                results = data.get("data", [])
                if not results:
                    break

                for r in results:
                    source_id = r.get("job_id", "")
                    if source_id in seen_ids:
                        continue
                    seen_ids.add(source_id)

                    # Parse posted date
                    posted = None
                    posted_str = r.get("job_posted_at_datetime_utc")
                    if posted_str:
                        try:
                            posted = datetime.fromisoformat(
                                posted_str.replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    # Determine location
                    loc_parts = [
                        r.get("job_city", ""),
                        r.get("job_state", ""),
                        r.get("job_country", ""),
                    ]
                    location_str = ", ".join(p for p in loc_parts if p)

                    job = ScrapedJob(
                        title=r.get("job_title", "Unknown"),
                        company=r.get("employer_name", "Unknown"),
                        location=location_str or None,
                        source="jsearch",
                        source_id=source_id,
                        apply_url=r.get("job_apply_link", "") or r.get("job_google_link", ""),
                        jd_text=r.get("job_description", ""),
                        salary_min=r.get("job_min_salary"),
                        salary_max=r.get("job_max_salary"),
                        posted_date=posted,
                        remote=r.get("job_is_remote", False),
                    )
                    job.ats_platform = job.detect_ats_platform()
                    all_jobs.append(job)

                logger.debug(f"JSearch: title='{title}' page={page} → {len(results)} results")

    logger.info(f"JSearch: scraped {len(all_jobs)} total jobs")
    return all_jobs
