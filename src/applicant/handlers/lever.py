"""
Lever ATS handler.
Lever forms: jobs.lever.co/{company}/{job_id}
Usually single-page with clear field structure.
"""
import asyncio
import random
from typing import Dict, Optional

from playwright.async_api import Page
from loguru import logger

from src.applicant.stealth import human_type, human_move_and_click
from src.db.models import Job


async def apply_lever(
    page: Page,
    profile: dict,
    resume_path: str,
    cover_letter: Optional[str],
    job: Job,
) -> Dict:
    """Apply to a Lever job posting."""
    personal = profile.get("personal", {})

    try:
        # Lever typically shows "Apply for this job" button
        apply_btn = await page.query_selector(
            'a.postings-btn, a[href*="apply"], .apply-button, '
            'a:has-text("Apply for this job")'
        )
        if apply_btn:
            await human_move_and_click(page, 'a.postings-btn, a[href*="apply"]')
            await asyncio.sleep(random.uniform(2, 4))

        # Lever standard fields
        fields = [
            ('input[name="name"]', "name",
             f"{personal.get('first_name', '')} {personal.get('last_name', '')}"),
            ('input[name="email"]', "email", personal.get("email", "")),
            ('input[name="phone"]', "default", personal.get("phone", "")),
            ('input[name="org"], input[name*="company"]', "default", ""),
            ('input[name*="linkedin"], input[placeholder*="LinkedIn"]', "default",
             personal.get("linkedin", "")),
            ('input[name*="github"], input[placeholder*="GitHub"]', "default",
             personal.get("github", "")),
            ('input[name*="website"], input[name*="portfolio"]', "default",
             personal.get("portfolio", "")),
        ]

        for selector, field_type, value in fields:
            if value:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        await human_type(page, selector, value, field_type)
                except Exception:
                    pass

        # Upload resume
        file_input = await page.query_selector(
            'input[type="file"][name="resume"], input[type="file"]'
        )
        if file_input:
            await file_input.set_input_files(resume_path)
            await asyncio.sleep(random.uniform(1.5, 3))
            logger.debug("Resume uploaded to Lever form")

        # Cover letter
        if cover_letter:
            cl_field = await page.query_selector(
                'textarea[name="comments"], textarea[name*="cover"]'
            )
            if cl_field and await cl_field.is_visible():
                await human_type(page, 'textarea[name="comments"]', cover_letter)

        # Handle additional questions (cards-based in Lever)
        await _fill_lever_cards(page, profile)

        # Review pause
        await asyncio.sleep(random.uniform(4, 8))

        # Submit
        submit_btn = await page.query_selector(
            'button[type="submit"], button:has-text("Submit"), '
            'button.postings-btn, input[type="submit"]'
        )
        if submit_btn:
            await human_move_and_click(page, 'button[type="submit"], button:has-text("Submit")')
            await asyncio.sleep(random.uniform(3, 6))

            # Check confirmation
            page_text = await page.inner_text("body")
            if any(w in page_text.lower() for w in ["thank", "submitted", "received", "confirmation"]):
                return {"success": True, "confirmation_number": "Lever submission confirmed"}

            return {"success": True, "confirmation_number": None}
        else:
            return {"success": False, "error": "Submit button not found"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _fill_lever_cards(page: Page, profile: dict):
    """Fill additional question cards in Lever forms."""
    form_answers = profile.get("form_answers", {})

    # Lever uses custom question cards — handle common patterns
    # Work authorization radio/select
    try:
        auth_options = await page.query_selector_all(
            'li:has-text("authorized to work") input[type="radio"], '
            'li:has-text("legally authorized") input[type="radio"]'
        )
        for opt in auth_options:
            label = await opt.evaluate('el => el.closest("li")?.textContent || ""')
            if "yes" in label.lower():
                await opt.click()
                break
    except Exception:
        pass

    # Sponsorship radio
    try:
        sponsor_options = await page.query_selector_all(
            'li:has-text("sponsor") input[type="radio"], '
            'li:has-text("visa") input[type="radio"]'
        )
        for opt in sponsor_options:
            label = await opt.evaluate('el => el.closest("li")?.textContent || ""')
            if "yes" in label.lower():
                await opt.click()
                break
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.5, 1.5))
