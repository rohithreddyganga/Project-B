"""
Base schema for normalized job listings + shared utilities.
"""
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ScrapedJob(BaseModel):
    """Normalized schema for a job from any source."""
    title: str
    company: str
    location: Optional[str] = None
    source: str                         # adzuna, jsearch, remoteok, greenhouse, lever
    source_id: Optional[str] = None     # ID from the source API
    apply_url: str
    jd_text: Optional[str] = None
    jd_html: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    posted_date: Optional[datetime] = None
    ats_platform: Optional[str] = None  # Detected ATS: workday, greenhouse, lever, etc.
    remote: bool = False

    @property
    def company_normalized(self) -> str:
        """Normalize company name for dedup and comparison."""
        name = self.company.lower().strip()
        # Remove common suffixes
        for suffix in [", inc.", ", inc", " inc.", " inc", ", llc", " llc",
                       ", ltd", " ltd", " corp.", " corp", " co.", " co",
                       ", l.p.", " l.p."]:
            name = name.replace(suffix, "")
        return re.sub(r'\s+', ' ', name).strip()

    @property
    def fingerprint(self) -> str:
        """SHA256 fingerprint for deduplication across sources."""
        raw = f"{self.company_normalized}|{self.title.lower().strip()}|{(self.location or '').lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def detect_ats_platform(self) -> Optional[str]:
        """Detect ATS platform from the apply URL."""
        url = self.apply_url.lower()
        patterns = {
            "workday": ["myworkdayjobs.com", "myworkday.com", "wd5.myworkday", "wd3.myworkday"],
            "greenhouse": ["boards.greenhouse.io", "greenhouse.io"],
            "lever": ["jobs.lever.co", "lever.co"],
            "icims": ["icims.com", "careers-"],
            "smartrecruiters": ["smartrecruiters.com", "jobs.smartrecruiters"],
            "taleo": ["taleo.net", "oracle.com/careers"],
            "ashby": ["jobs.ashby.io"],
            "bamboohr": ["bamboohr.com"],
            "jobvite": ["jobvite.com"],
        }
        for platform, signatures in patterns.items():
            if any(sig in url for sig in signatures):
                return platform
        return None
