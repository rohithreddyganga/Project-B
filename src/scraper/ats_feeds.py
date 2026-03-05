"""
ATS Platform Feed Scrapers — Greenhouse, Lever, SmartRecruiters.
These are PUBLIC APIs exposed by the platforms for exactly this purpose.
100% legal — no scraping, just API consumption.

No API keys needed — these are open board APIs.
"""
import re
import httpx
from datetime import datetime, timezone
from typing import List

from loguru import logger
from src.config import config
from src.scraper.base import ScrapedJob


# ── Greenhouse Board API ────────────────────────────────────


async def scrape_greenhouse(
    companies: List[str] | None = None,
    max_per_company: int = 50,
) -> List[ScrapedJob]:
    """
    Scrape jobs from Greenhouse Board API.
    boards-api.greenhouse.io/v1/boards/{company}/jobs
    FREE — no API key needed.
    """
    source_cfg = config.sources.get("greenhouse", {})
    if not source_cfg.get("enabled", False):
        logger.debug("Greenhouse source disabled in settings")
        return []

    companies = companies or source_cfg.get("companies", [])
    if not companies:
        logger.warning("Greenhouse: no target companies configured")
        return []

    query_terms = [q.lower() for q in config.job_criteria.get("titles", ["Software Engineer"])]
    all_jobs: List[ScrapedJob] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for company in companies:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
                resp = await client.get(url, params={"content": "true"})

                if resp.status_code == 404:
                    logger.warning(f"Greenhouse: company '{company}' not found")
                    continue
                resp.raise_for_status()
                data = resp.json()

                matched = 0
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    title_lower = title.lower()

                    # Filter by query relevance
                    if not any(t in title_lower for t in query_terms):
                        continue

                    loc_name = ""
                    if item.get("location", {}).get("name"):
                        loc_name = item["location"]["name"]

                    posted = None
                    if item.get("updated_at"):
                        try:
                            posted = datetime.fromisoformat(
                                item["updated_at"].replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except (ValueError, TypeError):
                            pass

                    content = item.get("content", "")

                    job = ScrapedJob(
                        title=title.strip(),
                        company=company.replace("-", " ").title(),
                        location=loc_name,
                        source="greenhouse",
                        source_id=str(item.get("id", "")),
                        apply_url=item.get("absolute_url", f"https://boards.greenhouse.io/{company}/jobs/{item.get('id')}"),
                        jd_text=_strip_html(content),
                        jd_html=content,
                        posted_date=posted,
                        ats_platform="greenhouse",
                        remote="remote" in loc_name.lower() or "remote" in title_lower,
                    )
                    all_jobs.append(job)
                    matched += 1

                    if matched >= max_per_company:
                        break

                logger.info(f"Greenhouse [{company}]: {len(data.get('jobs', []))} total, {matched} matched")

            except Exception as e:
                logger.error(f"Greenhouse [{company}] error: {e}")

    logger.info(f"Greenhouse: scraped {len(all_jobs)} matching jobs from {len(companies)} companies")
    return all_jobs


# ── Lever Postings API ──────────────────────────────────────


async def scrape_lever(
    companies: List[str] | None = None,
    max_per_company: int = 50,
) -> List[ScrapedJob]:
    """
    Scrape jobs from Lever Postings API.
    api.lever.co/v0/postings/{company}
    FREE — no API key needed.
    """
    source_cfg = config.sources.get("lever", {})
    if not source_cfg.get("enabled", False):
        logger.debug("Lever source disabled in settings")
        return []

    companies = companies or source_cfg.get("companies", [])
    if not companies:
        logger.warning("Lever: no target companies configured")
        return []

    query_terms = [q.lower() for q in config.job_criteria.get("titles", ["Software Engineer"])]
    all_jobs: List[ScrapedJob] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for company in companies:
            try:
                url = f"https://api.lever.co/v0/postings/{company}"
                resp = await client.get(url)

                if resp.status_code == 404:
                    logger.warning(f"Lever: company '{company}' not found")
                    continue
                resp.raise_for_status()
                data = resp.json()

                matched = 0
                for item in data:
                    title = item.get("text", "")
                    title_lower = title.lower()

                    if not any(t in title_lower for t in query_terms):
                        continue

                    loc = ""
                    if item.get("categories", {}).get("location"):
                        loc = item["categories"]["location"]

                    posted = None
                    if item.get("createdAt"):
                        try:
                            posted = datetime.fromtimestamp(
                                item["createdAt"] / 1000, tz=timezone.utc
                            ).replace(tzinfo=None)
                        except (ValueError, TypeError, OSError):
                            pass

                    # Build description from structured fields
                    desc_parts = []
                    if item.get("descriptionPlain"):
                        desc_parts.append(item["descriptionPlain"])
                    for lst in item.get("lists", []):
                        if lst.get("text"):
                            desc_parts.append(lst["text"])
                        if lst.get("content"):
                            desc_parts.append(_strip_html(lst["content"]))
                    description = "\n\n".join(desc_parts)

                    job = ScrapedJob(
                        title=title.strip(),
                        company=company.replace("-", " ").title(),
                        location=loc,
                        source="lever",
                        source_id=item.get("id", ""),
                        apply_url=item.get("hostedUrl", item.get("applyUrl", "")),
                        jd_text=description,
                        posted_date=posted,
                        ats_platform="lever",
                        remote="remote" in loc.lower() or "remote" in title_lower,
                    )
                    all_jobs.append(job)
                    matched += 1

                    if matched >= max_per_company:
                        break

                logger.info(f"Lever [{company}]: {len(data)} total, {matched} matched")

            except Exception as e:
                logger.error(f"Lever [{company}] error: {e}")

    logger.info(f"Lever: scraped {len(all_jobs)} matching jobs from {len(companies)} companies")
    return all_jobs


# ── SmartRecruiters Public API ──────────────────────────────


async def scrape_smartrecruiters(
    companies: List[str] | None = None,
    max_per_company: int = 50,
) -> List[ScrapedJob]:
    """
    Scrape jobs from SmartRecruiters Public API.
    api.smartrecruiters.com/v1/companies/{id}/postings
    FREE — no API key needed.
    """
    source_cfg = config.sources.get("smartrecruiters", {})
    if not source_cfg.get("enabled", False):
        logger.debug("SmartRecruiters source disabled in settings")
        return []

    companies = companies or source_cfg.get("companies", [])
    if not companies:
        logger.warning("SmartRecruiters: no target companies configured")
        return []

    query_terms = [q.lower() for q in config.job_criteria.get("titles", ["Software Engineer"])]
    all_jobs: List[ScrapedJob] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for company in companies:
            try:
                url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
                resp = await client.get(url, params={"limit": 100})

                if resp.status_code == 404:
                    logger.warning(f"SmartRecruiters: company '{company}' not found")
                    continue
                resp.raise_for_status()
                data = resp.json()

                matched = 0
                for item in data.get("content", []):
                    title = item.get("name", "")
                    title_lower = title.lower()

                    if not any(t in title_lower for t in query_terms):
                        continue

                    loc = ""
                    if item.get("location", {}).get("city"):
                        city = item["location"]["city"]
                        region = item["location"].get("region", "")
                        loc = f"{city}, {region}".strip(", ")

                    posted = None
                    if item.get("releasedDate"):
                        try:
                            posted = datetime.fromisoformat(
                                item["releasedDate"].replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except (ValueError, TypeError):
                            pass

                    # Description from jobAd sections
                    sections = item.get("jobAd", {}).get("sections", {})
                    desc = _strip_html(sections.get("jobDescription", {}).get("text", ""))
                    quals = _strip_html(sections.get("qualifications", {}).get("text", ""))
                    description = f"{desc}\n\nQualifications:\n{quals}" if quals else desc

                    company_name = item.get("company", {}).get("name", company.title())

                    job = ScrapedJob(
                        title=title.strip(),
                        company=company_name,
                        location=loc,
                        source="smartrecruiters",
                        source_id=item.get("id", ""),
                        apply_url=item.get("ref", f"https://jobs.smartrecruiters.com/{company}/{item.get('id', '')}"),
                        jd_text=description,
                        posted_date=posted,
                        ats_platform="smartrecruiters",
                        remote="remote" in loc.lower() or "remote" in title_lower,
                    )
                    all_jobs.append(job)
                    matched += 1

                    if matched >= max_per_company:
                        break

                logger.info(f"SmartRecruiters [{company}]: matched {matched} relevant jobs")

            except Exception as e:
                logger.error(f"SmartRecruiters [{company}] error: {e}")

    logger.info(f"SmartRecruiters: scraped {len(all_jobs)} matching jobs from {len(companies)} companies")
    return all_jobs


# ── Utilities ───────────────────────────────────────────────


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
