"""
Adzuna API scraper.
Free tier: 10,000 calls/month.
Docs: https://developer.adzuna.com/docs/search
"""
import httpx
from datetime import datetime, timezone
from typing import List

from loguru import logger
from src.config import config
from src.scraper.base import ScrapedJob


ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"


async def scrape_adzuna(
    titles: List[str] | None = None,
    location: str = "United States",
    max_results: int = 200,
) -> List[ScrapedJob]:
    """
    Scrape jobs from Adzuna API.
    Searches for each target title and deduplicates.
    """
    app_id = config.env.adzuna_app_id
    api_key = config.env.adzuna_api_key
    if not app_id or not api_key:
        logger.warning("Adzuna API keys not configured, skipping")
        return []

    source_cfg = config.sources.get("adzuna", {})
    if not source_cfg.get("enabled", True):
        return []

    country = source_cfg.get("country", "us")
    per_page = source_cfg.get("results_per_page", 50)
    max_pages = source_cfg.get("max_pages", 5)
    search_titles = titles or config.job_criteria.get("titles", ["Software Engineer"])

    all_jobs: List[ScrapedJob] = []
    seen_ids: set = set()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for title in search_titles:
            for page in range(1, max_pages + 1):
                if len(all_jobs) >= max_results:
                    break

                params = {
                    "app_id": app_id,
                    "app_key": api_key,
                    "results_per_page": per_page,
                    "page": page,
                    "what": title,
                    "where": location,
                    "sort_by": "date",           # Newest first
                    "max_days_old": 7,            # Last week only
                    "content-type": "application/json",
                }

                try:
                    url = f"{ADZUNA_BASE}/{country}/search/{page}"
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as e:
                    logger.error(f"Adzuna API error (title={title}, page={page}): {e}")
                    break

                results = data.get("results", [])
                if not results:
                    break

                for r in results:
                    source_id = str(r.get("id", ""))
                    if source_id in seen_ids:
                        continue
                    seen_ids.add(source_id)

                    # Parse posted date
                    posted = None
                    if r.get("created"):
                        try:
                            posted = datetime.fromisoformat(
                                r["created"].replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    job = ScrapedJob(
                        title=r.get("title", "Unknown"),
                        company=r.get("company", {}).get("display_name", "Unknown"),
                        location=r.get("location", {}).get("display_name", ""),
                        source="adzuna",
                        source_id=source_id,
                        apply_url=r.get("redirect_url", ""),
                        jd_text=r.get("description", ""),
                        salary_min=r.get("salary_min"),
                        salary_max=r.get("salary_max"),
                        posted_date=posted,
                        remote="remote" in r.get("title", "").lower()
                            or "remote" in r.get("location", {}).get("display_name", "").lower(),
                    )
                    job.ats_platform = job.detect_ats_platform()
                    all_jobs.append(job)

                logger.debug(f"Adzuna: title='{title}' page={page} → {len(results)} results")

    logger.info(f"Adzuna: scraped {len(all_jobs)} total jobs")
    return all_jobs
