"""
Jobs Search API scraper (via RapidAPI).
Provider: PR Labs — aggregates LinkedIn, Indeed, ZipRecruiter.
API: jobs-search-api.p.rapidapi.com

Similar to JSearch but different provider, often has different results.
Rate limit: ~500 requests/day on basic plan.
"""
import httpx
from datetime import datetime, timezone
from typing import List

from loguru import logger
from src.config import config
from src.scraper.base import ScrapedJob


JOBS_SEARCH_BASE = "https://jobs-search-api.p.rapidapi.com"


async def scrape_jobs_search_api(
    titles: List[str] | None = None,
    location: str = "United States",
    max_results: int = 100,
) -> List[ScrapedJob]:
    """
    Scrape jobs from Jobs Search API (RapidAPI / PR Labs).
    Aggregates LinkedIn, Indeed, and ZipRecruiter listings.
    """
    api_key = config.env.jsearch_api_key  # Same RapidAPI key
    if not api_key:
        logger.warning("RapidAPI key not configured, skipping Jobs Search API")
        return []

    source_cfg = config.sources.get("jobs_search_api", {})
    if not source_cfg.get("enabled", False):
        logger.debug("Jobs Search API source disabled in settings")
        return []

    search_titles = titles or config.job_criteria.get("titles", ["Software Engineer"])

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jobs-search-api.p.rapidapi.com",
    }

    all_jobs: List[ScrapedJob] = []
    seen_ids: set = set()
    rate_limited = False

    async with httpx.AsyncClient(timeout=30.0) as client:
        for title in search_titles:
            if len(all_jobs) >= max_results or rate_limited:
                break

            payload = {
                "search_term": title,
                "location": location,
                "results_wanted": 20,
                "site_name": ["indeed", "linkedin", "zip_recruiter"],
                "distance": 50,
                "job_type": "fulltime",
                "is_remote": False,
                "hours_old": 168,  # Last 7 days
            }

            try:
                resp = await client.post(
                    f"{JOBS_SEARCH_BASE}/search",
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload,
                )

                if resp.status_code == 429:
                    logger.warning("Jobs Search API rate limited — skipping")
                    rate_limited = True
                    break

                resp.raise_for_status()
                data = resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    rate_limited = True
                    break
                logger.warning(f"Jobs Search API error (title={title}): {e}")
                continue
            except httpx.HTTPError as e:
                logger.warning(f"Jobs Search API network error: {e}")
                continue

            # Parse — could be list or nested object
            results = data if isinstance(data, list) else data.get("jobs", data.get("data", data.get("results", [])))

            for r in results:
                if not isinstance(r, dict):
                    continue

                job_id = str(
                    r.get("id", "") or
                    r.get("job_id", "") or
                    r.get("external_id", "") or
                    ""
                )
                if not job_id:
                    job_id = str(hash(f"{r.get('title', '')}{r.get('company_name', '')}"))
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                apply_url = (
                    r.get("job_url", "") or
                    r.get("apply_url", "") or
                    r.get("url", "") or
                    r.get("link", "")
                )
                if not apply_url:
                    continue

                # Posted date
                posted = None
                date_str = r.get("date_posted", r.get("posted_date", r.get("created_at", "")))
                if date_str:
                    try:
                        posted = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                # Location
                loc = r.get("location", "")
                if isinstance(loc, dict):
                    parts = [loc.get("city", ""), loc.get("state", ""), loc.get("country", "")]
                    loc = ", ".join(p for p in parts if p)

                job = ScrapedJob(
                    title=r.get("title", r.get("job_title", "Unknown")),
                    company=r.get("company_name", r.get("company", r.get("employer_name", "Unknown"))),
                    location=str(loc) if loc else None,
                    source="jobs_search",
                    source_id=job_id,
                    apply_url=apply_url,
                    jd_text=r.get("description", r.get("job_description", "")),
                    salary_min=_safe_float(r.get("min_amount", r.get("salary_min"))),
                    salary_max=_safe_float(r.get("max_amount", r.get("salary_max"))),
                    posted_date=posted,
                    remote=r.get("is_remote", False) or "remote" in str(loc).lower(),
                )
                job.ats_platform = job.detect_ats_platform()
                all_jobs.append(job)

            logger.debug(f"Jobs Search API: title='{title}' → {len(results)} results")

    logger.info(f"Jobs Search API: scraped {len(all_jobs)} total jobs")
    return all_jobs


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
