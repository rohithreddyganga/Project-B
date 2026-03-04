"""
ATS Platform Feed Scrapers — Greenhouse, Lever, SmartRecruiters.
These are PUBLIC APIs exposed by the platforms for exactly this purpose.
100% legal — no scraping, just API consumption.
"""
import httpx
from datetime import datetime
from typing import List, Optional
from src.scraper.base import BaseScraper, ScrapedJob
from src.config import get_config
import logging

logger = logging.getLogger(__name__)


class GreenhouseScraper(BaseScraper):
    """Greenhouse Board API — boards-api.greenhouse.io/v1/boards/{company}/jobs"""
    
    @property
    def source_name(self) -> str:
        return "greenhouse"
    
    async def scrape(self, queries: List[str], locations: List[str]) -> List[ScrapedJob]:
        companies = get_config("scraping.target_companies.greenhouse", [])
        if not companies:
            return []
        
        jobs = []
        query_terms = [q.lower() for q in queries]
        
        async with httpx.AsyncClient(timeout=30) as client:
            for company in companies:
                try:
                    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
                    resp = await client.get(url, params={"content": "true"})
                    
                    if resp.status_code == 404:
                        logger.warning(f"Greenhouse: company '{company}' not found")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    
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
                            title=self.normalize_title(title),
                            company=company.replace("-", " ").title(),
                            location=loc_name,
                            description=_strip_html(content),
                            apply_url=item.get("absolute_url", f"https://boards.greenhouse.io/{company}/jobs/{item.get('id')}"),
                            source="greenhouse",
                            source_id=str(item.get("id", "")),
                            company_url=f"https://boards.greenhouse.io/{company}",
                            posted_date=posted,
                            remote="remote" in loc_name.lower() or "remote" in title_lower,
                        )
                        jobs.append(job)
                    
                    logger.info(f"Greenhouse [{company}]: {len(data.get('jobs', []))} total, {len([j for j in jobs if j.source_id])} matched")
                
                except Exception as e:
                    logger.error(f"Greenhouse [{company}] error: {e}")
        
        logger.info(f"Greenhouse total: {len(jobs)} matching jobs")
        return jobs


class LeverScraper(BaseScraper):
    """Lever Postings API — api.lever.co/v0/postings/{company}"""
    
    @property
    def source_name(self) -> str:
        return "lever"
    
    async def scrape(self, queries: List[str], locations: List[str]) -> List[ScrapedJob]:
        companies = get_config("scraping.target_companies.lever", [])
        if not companies:
            return []
        
        jobs = []
        query_terms = [q.lower() for q in queries]
        
        async with httpx.AsyncClient(timeout=30) as client:
            for company in companies:
                try:
                    url = f"https://api.lever.co/v0/postings/{company}"
                    resp = await client.get(url)
                    
                    if resp.status_code == 404:
                        logger.warning(f"Lever: company '{company}' not found")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    
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
                            posted = datetime.utcfromtimestamp(item["createdAt"] / 1000)
                        
                        desc_parts = []
                        for lst in item.get("lists", []):
                            desc_parts.append(lst.get("text", ""))
                            desc_parts.append(lst.get("content", ""))
                        description = "\n".join(desc_parts)
                        if item.get("descriptionPlain"):
                            description = item["descriptionPlain"] + "\n" + description
                        
                        job = ScrapedJob(
                            title=self.normalize_title(title),
                            company=company.replace("-", " ").title(),
                            location=loc,
                            description=description,
                            apply_url=item.get("hostedUrl", item.get("applyUrl", "")),
                            source="lever",
                            source_id=item.get("id", ""),
                            company_url=f"https://jobs.lever.co/{company}",
                            posted_date=posted,
                            remote="remote" in loc.lower() or "remote" in title_lower,
                        )
                        jobs.append(job)
                    
                    logger.info(f"Lever [{company}]: {len(data)} total, matched relevant")
                
                except Exception as e:
                    logger.error(f"Lever [{company}] error: {e}")
        
        logger.info(f"Lever total: {len(jobs)} matching jobs")
        return jobs


class SmartRecruitersScraper(BaseScraper):
    """SmartRecruiters Public API — api.smartrecruiters.com/v1/companies/{id}/postings"""
    
    @property
    def source_name(self) -> str:
        return "smartrecruiters"
    
    async def scrape(self, queries: List[str], locations: List[str]) -> List[ScrapedJob]:
        companies = get_config("scraping.target_companies.smartrecruiters", [])
        if not companies:
            return []
        
        jobs = []
        query_terms = [q.lower() for q in queries]
        
        async with httpx.AsyncClient(timeout=30) as client:
            for company in companies:
                try:
                    url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
                    resp = await client.get(url, params={"limit": 100})
                    
                    if resp.status_code == 404:
                        logger.warning(f"SmartRecruiters: company '{company}' not found")
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    
                    for item in data.get("content", []):
                        title = item.get("name", "")
                        title_lower = title.lower()
                        
                        if not any(t in title_lower for t in query_terms):
                            continue
                        
                        loc = ""
                        if item.get("location", {}).get("city"):
                            loc = f"{item['location']['city']}, {item['location'].get('region', '')}"
                        
                        posted = None
                        if item.get("releasedDate"):
                            try:
                                posted = datetime.fromisoformat(
                                    item["releasedDate"].replace("Z", "+00:00")
                                ).replace(tzinfo=None)
                            except (ValueError, TypeError):
                                pass
                        
                        sections = item.get("jobAd", {}).get("sections", {})
                        desc = sections.get("jobDescription", {}).get("text", "")
                        quals = sections.get("qualifications", {}).get("text", "")
                        description = f"{desc}\n\nQualifications:\n{quals}"
                        
                        job = ScrapedJob(
                            title=self.normalize_title(title),
                            company=item.get("company", {}).get("name", company.title()),
                            location=loc.strip(", "),
                            description=description,
                            apply_url=item.get("ref", f"https://jobs.smartrecruiters.com/{company}/{item.get('id','')}"),
                            source="smartrecruiters",
                            source_id=item.get("id", ""),
                            posted_date=posted,
                            remote="remote" in loc.lower() or "remote" in title_lower,
                        )
                        jobs.append(job)
                    
                    logger.info(f"SmartRecruiters [{company}]: matched {len(jobs)} relevant jobs")
                
                except Exception as e:
                    logger.error(f"SmartRecruiters [{company}] error: {e}")
        
        logger.info(f"SmartRecruiters total: {len(jobs)} matching jobs")
        return jobs


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
