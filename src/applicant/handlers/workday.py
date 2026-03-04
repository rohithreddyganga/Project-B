"""
Workday ATS handler.
Workday is the most complex ATS — multi-page, heavily JS-rendered.
URLs: myworkdayjobs.com, wd5.myworkday.com, etc.

Strategy: Navigate through multi-step wizard, handle dynamic loading.
"""
import asyncio
import random
from typing import Dict, Optional

from playwright.async_api import Page
from loguru import logger

from src.applicant.stealth import human_type, human_move_and_click
from src.db.models import Job


async def apply_workday(
    page: Page,
    profile: dict,
    resume_path: str,
    cover_letter: Optional[str],
    job: Job,
) -> Dict:
    """Apply to a Workday job posting."""
    personal = profile.get("personal", {})
    form_answers = profile.get("form_answers", {})

    try:
        # ── Step 1: Click Apply ─────────────────────────
        # Workday has various Apply button patterns
        apply_selectors = [
            'a[data-automation-id="jobPostingApplyButton"]',
            'button[data-automation-id="jobPostingApplyButton"]',
            'a:has-text("Apply")',
            'button:has-text("Apply")',
        ]
        for sel in apply_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await human_move_and_click(page, sel)
                await asyncio.sleep(random.uniform(3, 5))
                break

        # ── Step 2: Handle "Sign In" vs "Create Account" ──
        # Many Workday sites require account creation
        create_btn = await page.query_selector(
            'a:has-text("Create Account"), '
            'button:has-text("Create Account"), '
            'a[data-automation-id="createAccountLink"]'
        )
        if create_btn and await create_btn.is_visible():
            # Try "Apply Manually" or "Upload Resume" first
            manual_btn = await page.query_selector(
                'button:has-text("Apply Manually"), '
                'a:has-text("Apply Manually")'
            )
            if manual_btn:
                await human_move_and_click(page, 'button:has-text("Apply Manually")')
            else:
                await human_move_and_click(page, 'a:has-text("Create Account")')
            await asyncio.sleep(random.uniform(2, 4))

        # ── Step 3: Upload Resume (often first step) ────
        await _upload_resume_workday(page, resume_path)
        await asyncio.sleep(random.uniform(2, 4))

        # ── Step 4: Fill Personal Information ───────────
        await _fill_personal_info(page, personal)
        await asyncio.sleep(random.uniform(1, 2))

        # ── Step 5: Try to advance through wizard pages ─
        max_pages = 6  # Workday wizards typically have 3-6 pages
        for step in range(max_pages):
            # Fill any visible form fields on current page
            await _fill_current_page(page, personal, form_answers)
            await asyncio.sleep(random.uniform(1.5, 3))

            # Look for Next/Continue button
            next_btn = await page.query_selector(
                'button[data-automation-id="bottom-navigation-next-button"], '
                'button:has-text("Next"), '
                'button:has-text("Continue"), '
                'button:has-text("Save and Continue")'
            )
            if next_btn and await next_btn.is_visible():
                await human_move_and_click(
                    page,
                    'button[data-automation-id="bottom-navigation-next-button"], '
                    'button:has-text("Next")'
                )
                await asyncio.sleep(random.uniform(2, 4))
            else:
                break  # No more pages

        # ── Step 6: Review & Submit ─────────────────────
        await asyncio.sleep(random.uniform(3, 6))

        # Handle checkboxes (terms, agreements)
        checkboxes = await page.query_selector_all(
            'input[type="checkbox"]:not(:checked)'
        )
        for cb in checkboxes:
            try:
                if await cb.is_visible():
                    await cb.click()
                    await asyncio.sleep(random.uniform(0.3, 0.8))
            except Exception:
                pass

        # Submit
        submit_selectors = [
            'button[data-automation-id="bottom-navigation-next-button"]:has-text("Submit")',
            'button:has-text("Submit Application")',
            'button:has-text("Submit")',
            'button[type="submit"]',
        ]
        for sel in submit_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await human_move_and_click(page, sel)
                await asyncio.sleep(random.uniform(4, 8))
                break

        # ── Step 7: Check confirmation ──────────────────
        confirmation = await _check_workday_confirmation(page)
        if confirmation:
            return {"success": True, "confirmation_number": confirmation}

        return {"success": True, "confirmation_number": None}

    except Exception as e:
        return {"success": False, "error": f"Workday: {str(e)}"}


async def _upload_resume_workday(page: Page, resume_path: str):
    """Handle Workday's resume upload (often drag-drop or file picker)."""
    # Try standard file input first
    file_selectors = [
        'input[type="file"][data-automation-id="file-upload-input-ref"]',
        'input[type="file"][data-automation-id="resumeFileUpload"]',
        'input[type="file"]',
    ]
    for sel in file_selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.set_input_files(resume_path)
                logger.debug("Resume uploaded to Workday form")
                # Wait for parsing
                await asyncio.sleep(random.uniform(3, 6))
                return
        except Exception:
            continue

    # Try clicking upload button first to reveal file input
    upload_btn = await page.query_selector(
        'button[data-automation-id="attachmentButton"], '
        'button:has-text("Upload"), '
        'div[data-automation-id="file-upload-drop-zone"]'
    )
    if upload_btn:
        await upload_btn.click()
        await asyncio.sleep(1)
        # Try file input again
        el = await page.query_selector('input[type="file"]')
        if el:
            await el.set_input_files(resume_path)
            await asyncio.sleep(random.uniform(3, 6))


async def _fill_personal_info(page: Page, personal: dict):
    """Fill Workday personal information fields."""
    # Workday uses data-automation-id attributes extensively
    field_map = {
        '[data-automation-id="legalNameSection_firstName"], input[aria-label*="First Name"]':
            personal.get("first_name", ""),
        '[data-automation-id="legalNameSection_lastName"], input[aria-label*="Last Name"]':
            personal.get("last_name", ""),
        '[data-automation-id="email"], input[aria-label*="Email"]':
            personal.get("email", ""),
        '[data-automation-id="phone-number"], input[aria-label*="Phone"]':
            personal.get("phone", ""),
        'input[aria-label*="LinkedIn"], input[data-automation-id*="linkedin"]':
            personal.get("linkedin", ""),
        'input[aria-label*="Address Line 1"]':
            personal.get("location", {}).get("address", ""),
        'input[aria-label*="City"]':
            personal.get("location", {}).get("city", ""),
        'input[aria-label*="Postal"]':
            personal.get("location", {}).get("zip", ""),
    }

    for selector, value in field_map.items():
        if not value:
            continue
        try:
            el = await page.query_selector(selector)
            if el and await el.is_visible():
                await el.click()
                await asyncio.sleep(0.2)
                await el.fill("")  # Clear first
                await human_type(page, selector, value, "default")
                await asyncio.sleep(random.uniform(0.3, 0.8))
        except Exception:
            pass


async def _fill_current_page(page: Page, personal: dict, form_answers: dict):
    """Fill visible form fields on the current Workday wizard page."""
    # Handle dropdowns (Country, State, etc.)
    dropdowns = await page.query_selector_all(
        'button[data-automation-id*="dropdown"], '
        'div[data-automation-id*="select"]'
    )
    for dd in dropdowns:
        try:
            label_text = await dd.evaluate(
                'el => el.closest("[data-automation-id]")?.getAttribute("aria-label") || ""'
            )
            if not label_text:
                continue

            label_lower = label_text.lower()
            if "country" in label_lower:
                await _select_workday_dropdown(page, dd, "United States of America")
            elif "state" in label_lower:
                state = personal.get("location", {}).get("state", "")
                if state:
                    await _select_workday_dropdown(page, dd, state)
        except Exception:
            pass

    # Handle radio buttons / checkboxes for common questions
    await _answer_workday_questions(page, form_answers)


async def _select_workday_dropdown(page: Page, dropdown_el, value: str):
    """Select a value from a Workday custom dropdown."""
    try:
        await dropdown_el.click()
        await asyncio.sleep(0.5)

        # Type to search in dropdown
        option = await page.query_selector(f'div[data-automation-id="promptOption"]:has-text("{value}")')
        if option:
            await option.click()
            await asyncio.sleep(0.3)
    except Exception:
        pass


async def _answer_workday_questions(page: Page, form_answers: dict):
    """Handle common Workday screening questions."""
    # Work authorization
    auth_q = await page.query_selector(
        'div:has-text("authorized to work") input[type="radio"][value="1"], '
        'div:has-text("legally authorized") input[type="radio"][value="Yes"]'
    )
    if auth_q:
        try:
            await auth_q.click()
        except Exception:
            pass

    # Sponsorship
    sponsor_q = await page.query_selector(
        'div:has-text("sponsorship") input[type="radio"][value="1"], '
        'div:has-text("sponsor") input[type="radio"][value="Yes"]'
    )
    if sponsor_q:
        try:
            await sponsor_q.click()
        except Exception:
            pass

    await asyncio.sleep(random.uniform(0.5, 1))


async def _check_workday_confirmation(page: Page) -> Optional[str]:
    """Check for Workday submission confirmation."""
    try:
        # Workday confirmation patterns
        conf_selectors = [
            'div[data-automation-id="congratulationsLabel"]',
            'h2:has-text("Thank")',
            'div:has-text("successfully submitted")',
            'div:has-text("Application Submitted")',
            'div[data-automation-id="applicationConfirmation"]',
        ]
        for sel in conf_selectors:
            el = await page.query_selector(sel)
            if el:
                text = await el.inner_text()
                return text[:100] if text else "Workday confirmation"

        if any(w in page.url.lower() for w in ["thank", "confirm", "success"]):
            return "Confirmed (URL)"
    except Exception:
        pass
    return None
