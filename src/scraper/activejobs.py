"""
Active Jobs DB scraper (via RapidAPI).
Provider: Fantastic.Jobs — 170k+ career sites & ATS.
API: active-jobs-db.p.rapidapi.com

Features: AI-enriched, hourly refresh, text & structured data.
Rate limit: ~1,000 requests/day on basic plan.
"""
import httpx
from datetime import datetime, timezone
from typing import List

from loguru import logger
from src.config import config
from src.scraper.base import ScrapedJob


ACTIVEJOBS_BASE = "https://active-jobs-db.p.rapidapi.com"


async def scrape_activejobs(
    titles: List[str] | None = None,
    location: str = "United States",
    max_results: int = 150,
) -> List[ScrapedJob]:
    """
    Scrape jobs from Active Jobs DB API (RapidAPI).
    170k+ career sites with structured data.
    """
    api_key = config.env.jsearch_api_key  # Same RapidAPI key
    if not api_key:
        logger.warning("RapidAPI key not configured, skipping Active Jobs DB")
        return []

    source_cfg = config.sources.get("activejobs", {})
    if not source_cfg.get("enabled", False):
        logger.debug("Active Jobs DB source disabled in settings")
        return []

    search_titles = titles or config.job_criteria.get("titles", ["Software Engineer"])
    per_page = source_cfg.get("results_per_page", 20)

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "active-jobs-db.p.rapidapi.com",
    }

    all_jobs: List[ScrapedJob] = []
    seen_ids: set = set()
    rate_limited = False

    async with httpx.AsyncClient(timeout=30.0) as client:
        for title in search_titles:
            if len(all_jobs) >= max_results or rate_limited:
                break

            # Active Jobs DB uses POST with JSON body
            payload = {
                "title": title,
                "location": location,
                "page": "1",
                "results_per_page": str(per_page),
            }

            try:
                # Try both GET and POST patterns (API may support either)
                resp = await client.get(
                    f"{ACTIVEJOBS_BASE}/active-ats-7d",
                    headers=headers,
                    params={
                        "title": title,
                        "location": location,
                        "page": "1",
                    },
                )

                if resp.status_code == 429:
                    logger.warning("Active Jobs DB rate limited — skipping")
                    rate_limited = True
                    break

                resp.raise_for_status()
                data = resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    rate_limited = True
                    break
                logger.warning(f"Active Jobs DB error (title={title}): {e}")
                continue
            except httpx.HTTPError as e:
                logger.warning(f"Active Jobs DB network error: {e}")
                continue

            # Parse response
            results = data if isinstance(data, list) else data.get("data", data.get("jobs", []))

            for r in results:
                if not isinstance(r, dict):
                    continue

                job_id = str(
                    r.get("id", "") or
                    r.get("job_id", "") or
                    r.get("external_id", "") or
                    hash(f"{r.get('title', '')}{r.get('company', '')}")
                )
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # Apply URL
                apply_url = (
                    r.get("apply_url", "") or
                    r.get("url", "") or
                    r.get("job_url", "") or
                    r.get("link", "")
                )
                if not apply_url:
                    continue

                # Posted date
                posted = None
                for date_key in ["posted_date", "date_posted", "created_at", "published_at"]:
                    date_val = r.get(date_key)
                    if date_val:
                        try:
                            if isinstance(date_val, (int, float)):
                                posted = datetime.fromtimestamp(date_val, tz=timezone.utc)
                            else:
                                posted = datetime.fromisoformat(
                                    str(date_val).replace("Z", "+00:00")
                                )
                            break
                        except (ValueError, TypeError, OSError):
                            continue

                # Company name
                company = r.get("company", r.get("company_name", r.get("employer", "Unknown")))
                if isinstance(company, dict):
                    company = company.get("name", "Unknown")

                # Location
                loc = r.get("location", r.get("job_location", ""))
                if isinstance(loc, dict):
                    parts = [loc.get("city", ""), loc.get("state", ""), loc.get("country", "")]
                    loc = ", ".join(p for p in parts if p)

                # Description — may be in various fields
                description = (
                    r.get("description", "") or
                    r.get("job_description", "") or
                    r.get("text", "") or
                    r.get("body", "")
                )

                job = ScrapedJob(
                    title=r.get("title", r.get("job_title", "Unknown")),
                    company=str(company),
                    location=str(loc) if loc else None,
                    source="activejobs",
                    source_id=job_id,
                    apply_url=apply_url,
                    jd_text=str(description),
                    salary_min=_safe_float(r.get("salary_min", r.get("min_salary"))),
                    salary_max=_safe_float(r.get("salary_max", r.get("max_salary"))),
                    posted_date=posted,
                    remote="remote" in str(r.get("remote", r.get("location", ""))).lower(),
                )
                job.ats_platform = job.detect_ats_platform()
                all_jobs.append(job)

            logger.debug(f"Active Jobs DB: title='{title}' → {len(results)} results")

    logger.info(f"Active Jobs DB: scraped {len(all_jobs)} total jobs")
    return all_jobs


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
