"""
Auto Applicant Engine — orchestrates end-to-end form filling.
Strategy 1: Dedicated ATS handlers (Greenhouse, Lever, Workday, iCIMS, SmartRecruiters, Taleo)
Strategy 2: Browser-Use AI fallback for unknown portals.

Phase 2: Added Workday, iCIMS, SmartRecruiters, Taleo handlers.
"""
import asyncio
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional, Dict
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from src.config import config
from src.db.models import Job, Application, JobStatus
from src.applicant.stealth import apply_stealth, human_scroll_read
from src.applicant.handlers.greenhouse import apply_greenhouse
from src.applicant.handlers.lever import apply_lever
from src.applicant.handlers.workday import apply_workday
from src.applicant.handlers.icims import apply_icims
from src.applicant.handlers.smartrecruiters import apply_smartrecruiters
from src.applicant.handlers.taleo import apply_taleo
from src.applicant.handlers.generic import apply_generic


# Map ATS platform to handler — all 6 now active
ATS_HANDLERS = {
    "greenhouse": apply_greenhouse,
    "lever": apply_lever,
    "workday": apply_workday,
    "icims": apply_icims,
    "smartrecruiters": apply_smartrecruiters,
    "taleo": apply_taleo,
}


class ApplicationEngine:
    """Manages the browser and applies to jobs."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self):
        """Launch the browser with stealth patches."""
        self._playwright = await async_playwright().start()

        user_data_dir = os.path.expanduser("~/.autoapply/browser_data")
        os.makedirs(user_data_dir, exist_ok=True)

        self._browser = await self._playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1920,1080",
            ],
        )

        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
        )

        await apply_stealth(self._context)
        logger.info(
            f"Application engine started — "
            f"{len(ATS_HANDLERS)} ATS handlers active: "
            f"{', '.join(ATS_HANDLERS.keys())}"
        )

    async def stop(self):
        """Close the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Application engine stopped")

    async def apply_to_job(
        self,
        job: Job,
        resume_path: str,
        cover_letter: Optional[str] = None,
    ) -> Dict:
        """
        Apply to a single job. Returns result dict.
        Selects the appropriate handler based on ATS platform.
        """
        if not self._context:
            await self.start()

        page = await self._context.new_page()

        result = {
            "success": False,
            "screenshot_path": None,
            "confirmation_number": None,
            "error": None,
        }

        try:
            logger.info(f"Applying: {job.company} — {job.title} ({job.apply_url[:60]}...)")
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)

            # Simulate reading the job description
            await human_scroll_read(page)

            # Load profile data
            profile = config.profile

            # Select handler — try detected platform first, then re-detect from URL
            platform = (job.ats_platform or "").lower()

            # If no platform detected yet, try to detect from current URL
            if not platform or platform not in ATS_HANDLERS:
                platform = _detect_platform_from_url(page.url)

            handler = ATS_HANDLERS.get(platform, apply_generic)
            handler_name = platform if platform in ATS_HANDLERS else "generic"

            logger.info(f"Using handler: {handler_name}")

            # Apply
            apply_result = await handler(
                page=page,
                profile=profile,
                resume_path=resume_path,
                cover_letter=cover_letter,
                job=job,
            )

            result["success"] = apply_result.get("success", False)
            result["confirmation_number"] = apply_result.get("confirmation_number")

            # Take screenshot
            if result["success"]:
                screenshot_dir = tempfile.mkdtemp(prefix="screenshot_")
                screenshot_path = os.path.join(screenshot_dir, "confirmation.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                result["screenshot_path"] = screenshot_path
                logger.info(f"✅ Applied successfully: {job.company} — {job.title} (via {handler_name})")
            else:
                result["error"] = apply_result.get("error", "Unknown application error")
                logger.warning(f"❌ Application failed: {job.company} — {result['error']}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Application error: {job.company} — {job.title}: {e}")

            try:
                err_dir = tempfile.mkdtemp(prefix="error_")
                await page.screenshot(
                    path=os.path.join(err_dir, "error.png"), full_page=True
                )
            except Exception:
                pass

        finally:
            await page.close()

        return result


def _detect_platform_from_url(url: str) -> str:
    """Detect ATS platform from the current page URL (may have redirected)."""
    url_lower = url.lower()
    patterns = {
        "workday": ["myworkdayjobs.com", "myworkday.com", "wd5.myworkday", "wd3.myworkday"],
        "greenhouse": ["boards.greenhouse.io", "greenhouse.io"],
        "lever": ["jobs.lever.co", "lever.co"],
        "icims": ["icims.com", "careers-"],
        "smartrecruiters": ["smartrecruiters.com", "jobs.smartrecruiters"],
        "taleo": ["taleo.net", "oracle.com/careers"],
    }
    for platform, signatures in patterns.items():
        if any(sig in url_lower for sig in signatures):
            return platform
    return ""


# Singleton
application_engine = ApplicationEngine()
