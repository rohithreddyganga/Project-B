"""
Auto Applicant Engine — orchestrates end-to-end form filling.
Strategy 1: Dedicated ATS handlers (Greenhouse, Lever, Workday, etc.)
Strategy 2: Browser-Use AI fallback for unknown portals.
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
from src.applicant.handlers.generic import apply_generic


# Map ATS platform to handler
ATS_HANDLERS = {
    "greenhouse": apply_greenhouse,
    "lever": apply_lever,
    # "workday": apply_workday,     # Phase 2
    # "icims": apply_icims,         # Phase 2
    # "smartrecruiters": apply_sr,  # Phase 2
    # "taleo": apply_taleo,         # Phase 2
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

        # Use persistent context for cookie/session persistence
        user_data_dir = os.path.expanduser("~/.autoapply/browser_data")
        os.makedirs(user_data_dir, exist_ok=True)

        self._browser = await self._playwright.chromium.launch(
            headless=False,  # Always headed (Xvfb in production)
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
        logger.info("Application engine started (browser ready)")

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
            # Navigate to the job page
            logger.info(f"Applying: {job.company} — {job.title} ({job.apply_url[:60]}...)")
            await page.goto(job.apply_url, wait_until="domcontentloaded", timeout=30000)

            # Simulate reading the job description
            await human_scroll_read(page)

            # Load profile data for form filling
            profile = config.profile

            # Select handler
            platform = (job.ats_platform or "").lower()
            handler = ATS_HANDLERS.get(platform, apply_generic)

            logger.debug(f"Using handler: {platform or 'generic'}")

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
                logger.info(f"Applied successfully: {job.company} — {job.title}")
            else:
                result["error"] = apply_result.get("error", "Unknown application error")
                logger.warning(f"Application failed: {job.company} — {result['error']}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Application error: {job.company} — {job.title}: {e}")

            # Take error screenshot
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


# Singleton
application_engine = ApplicationEngine()
