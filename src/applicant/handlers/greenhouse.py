"""
Greenhouse ATS handler.
Greenhouse forms are relatively standardized:
  - boards.greenhouse.io/{company}/jobs/{id}
  - Application form loads inline or in a separate page
"""
import asyncio
import random
from typing import Dict, Optional

from playwright.async_api import Page
from loguru import logger

from src.applicant.stealth import human_type, human_move_and_click
from src.db.models import Job


async def apply_greenhouse(
    page: Page,
    profile: dict,
    resume_path: str,
    cover_letter: Optional[str],
    job: Job,
) -> Dict:
    """Apply to a Greenhouse job posting."""
    personal = profile.get("personal", {})
    form_answers = profile.get("form_answers", {})

    try:
        # Wait for the application form to load
        # Greenhouse typically has an "Apply" button that opens the form
        apply_btn = await page.query_selector(
            'a[href*="application"], button:has-text("Apply"), '
            'a:has-text("Apply for this job"), a:has-text("Apply Now")'
        )
        if apply_btn:
            await human_move_and_click(page, 'a[href*="application"], button:has-text("Apply")')
            await asyncio.sleep(random.uniform(2, 4))

        # Fill standard fields
        field_map = {
            '#first_name, input[name*="first_name"], input[autocomplete="given-name"]':
                ("name", personal.get("first_name", "")),
            '#last_name, input[name*="last_name"], input[autocomplete="family-name"]':
                ("name", personal.get("last_name", "")),
            '#email, input[name*="email"], input[type="email"]':
                ("email", personal.get("email", "")),
            '#phone, input[name*="phone"], input[type="tel"]':
                ("default", personal.get("phone", "")),
            'input[name*="linkedin"], input[placeholder*="LinkedIn"]':
                ("default", personal.get("linkedin", "")),
            'input[name*="github"], input[placeholder*="GitHub"]':
                ("default", personal.get("github", "")),
            'input[name*="website"], input[name*="portfolio"]':
                ("default", personal.get("portfolio", "")),
        }

        for selector, (field_type, value) in field_map.items():
            if value:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        await human_type(page, selector, value, field_type)
                except Exception:
                    pass

        # Upload resume
        file_input = await page.query_selector(
            'input[type="file"][name*="resume"], input[type="file"]:first-of-type'
        )
        if file_input:
            await file_input.set_input_files(resume_path)
            await asyncio.sleep(random.uniform(1, 2))
            logger.debug("Resume uploaded to Greenhouse form")

        # Fill cover letter if field exists
        if cover_letter:
            cl_field = await page.query_selector(
                'textarea[name*="cover_letter"], textarea[placeholder*="Cover"]'
            )
            if cl_field and await cl_field.is_visible():
                await human_type(page, 'textarea[name*="cover_letter"]', cover_letter)

        # Handle common additional questions
        await _fill_additional_fields(page, form_answers)

        # Pause before submission (simulate review)
        await asyncio.sleep(random.uniform(3, 8))

        # Submit
        submit_btn = await page.query_selector(
            'button[type="submit"], input[type="submit"], '
            'button:has-text("Submit Application"), button:has-text("Submit")'
        )
        if submit_btn:
            await human_move_and_click(
                page, 'button[type="submit"], input[type="submit"], button:has-text("Submit")'
            )
            await asyncio.sleep(random.uniform(3, 6))

            # Check for confirmation
            confirmation = await _check_confirmation(page)
            return {"success": True, "confirmation_number": confirmation}
        else:
            return {"success": False, "error": "Submit button not found"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _fill_additional_fields(page: Page, form_answers: dict):
    """Handle common Greenhouse additional questions (sponsorship, EEO, etc.)."""
    # Work authorization questions
    auth_selectors = [
        'select[name*="authorized"], select[name*="work_auth"]',
        'select:has(option:has-text("authorized to work"))',
    ]
    for sel in auth_selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.select_option(label="Yes")
                break
        except Exception:
            pass

    # Sponsorship question
    sponsor_selectors = [
        'select[name*="sponsor"], select[name*="visa"]',
    ]
    for sel in sponsor_selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.select_option(label="Yes")
                break
        except Exception:
            pass

    # Small delay between field groups
    await asyncio.sleep(random.uniform(0.5, 1.5))


async def _check_confirmation(page: Page) -> Optional[str]:
    """Check for application confirmation on the page."""
    try:
        # Look for common confirmation indicators
        confirmation_selectors = [
            'text="Thank you"',
            'text="Application submitted"',
            'text="successfully submitted"',
            'text="received your application"',
            '.confirmation',
        ]
        for sel in confirmation_selectors:
            el = await page.query_selector(sel)
            if el:
                text = await el.inner_text()
                return text[:100] if text else "Confirmed"

        # Check URL changed to a confirmation page
        if "thank" in page.url.lower() or "confirm" in page.url.lower():
            return "Confirmed (URL)"

    except Exception:
        pass

    return None
