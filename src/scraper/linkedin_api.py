"""
LinkedIn Job Search API scraper (via RapidAPI).
Provider: Fantastic.Jobs — 8M+ AI-enriched LinkedIn jobs.
API: linkedin-job-search-api.p.rapidapi.com

Features: Apply URLs, company info, hourly refresh.
Rate limit: ~500 requests/day on basic plan.
"""
import httpx
from datetime import datetime, timezone
from typing import List

from loguru import logger
from src.config import config
from src.scraper.base import ScrapedJob


LINKEDIN_API_BASE = "https://linkedin-job-search-api.p.rapidapi.com"


async def scrape_linkedin_api(
    titles: List[str] | None = None,
    location: str = "United States",
    max_results: int = 100,
) -> List[ScrapedJob]:
    """
    Scrape jobs from LinkedIn Job Search API (RapidAPI).
    Returns AI-enriched LinkedIn jobs with apply URLs.
    """
    api_key = config.env.jsearch_api_key  # Same RapidAPI key works
    if not api_key:
        logger.warning("RapidAPI key not configured, skipping LinkedIn API")
        return []

    source_cfg = config.sources.get("linkedin_api", {})
    if not source_cfg.get("enabled", False):
        logger.debug("LinkedIn API source disabled in settings")
        return []

    search_titles = titles or config.job_criteria.get("titles", ["Software Engineer"])
    per_page = source_cfg.get("results_per_page", 25)

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "linkedin-job-search-api.p.rapidapi.com",
    }

    all_jobs: List[ScrapedJob] = []
    seen_ids: set = set()
    rate_limited = False

    async with httpx.AsyncClient(timeout=30.0) as client:
        for title in search_titles:
            if len(all_jobs) >= max_results or rate_limited:
                break

            params = {
                "keywords": title,
                "locationId": "103644278",  # United States
                "datePosted": "pastWeek",
                "sort": "mostRelevant",
                "start": "0",
            }

            try:
                # Try the search endpoint
                resp = await client.get(
                    f"{LINKEDIN_API_BASE}/search-jobs",
                    headers=headers,
                    params=params,
                )

                if resp.status_code == 429:
                    logger.warning("LinkedIn API rate limited — skipping remaining titles")
                    rate_limited = True
                    break

                resp.raise_for_status()
                data = resp.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("LinkedIn API rate limited")
                    rate_limited = True
                    break
                logger.warning(f"LinkedIn API error (title={title}): {e}")
                continue
            except httpx.HTTPError as e:
                logger.warning(f"LinkedIn API network error: {e}")
                continue

            # Parse response — API returns list of job objects
            results = data if isinstance(data, list) else data.get("data", data.get("jobs", []))

            for r in results:
                if not isinstance(r, dict):
                    continue

                job_id = str(r.get("id", r.get("jobId", r.get("job_id", ""))))
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # Extract apply URL — prefer direct, fallback to LinkedIn
                apply_url = (
                    r.get("applyUrl", "") or
                    r.get("apply_url", "") or
                    r.get("url", "") or
                    r.get("jobUrl", "") or
                    f"https://www.linkedin.com/jobs/view/{job_id}"
                )

                # Parse posted date
                posted = None
                posted_str = r.get("postedDate", r.get("posted_at", r.get("listedAt", "")))
                if posted_str:
                    try:
                        if isinstance(posted_str, (int, float)):
                            posted = datetime.fromtimestamp(posted_str / 1000, tz=timezone.utc)
                        else:
                            posted = datetime.fromisoformat(str(posted_str).replace("Z", "+00:00"))
                    except (ValueError, TypeError, OSError):
                        pass

                # Location
                loc = r.get("location", r.get("formattedLocation", ""))
                if isinstance(loc, dict):
                    loc = f"{loc.get('city', '')}, {loc.get('state', '')}, {loc.get('country', '')}"

                # Company
                company = r.get("company", r.get("companyName", r.get("employer", "")))
                if isinstance(company, dict):
                    company = company.get("name", company.get("companyName", "Unknown"))

                job = ScrapedJob(
                    title=r.get("title", r.get("jobTitle", "Unknown")),
                    company=str(company) if company else "Unknown",
                    location=str(loc) if loc else None,
                    source="linkedin_api",
                    source_id=job_id,
                    apply_url=apply_url,
                    jd_text=r.get("description", r.get("jobDescription", "")),
                    salary_min=_parse_salary(r.get("salaryMin", r.get("salary", {}).get("min"))),
                    salary_max=_parse_salary(r.get("salaryMax", r.get("salary", {}).get("max"))),
                    posted_date=posted,
                    remote="remote" in str(r.get("workplaceType", r.get("location", ""))).lower(),
                )
                job.ats_platform = job.detect_ats_platform()
                all_jobs.append(job)

            logger.debug(f"LinkedIn API: title='{title}' → {len(results)} results")

    logger.info(f"LinkedIn API: scraped {len(all_jobs)} total jobs")
    return all_jobs


def _parse_salary(val) -> float | None:
    """Parse salary from various formats."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
