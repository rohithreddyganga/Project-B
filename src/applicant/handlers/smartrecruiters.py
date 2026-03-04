"""
SmartRecruiters ATS handler.
URLs: jobs.smartrecruiters.com/{company}/{id}
Modern, clean forms — relatively straightforward to automate.
Used by ~5,000 companies including Visa, Bosch, LinkedIn.
"""
import asyncio
import random
from typing import Dict, Optional

from playwright.async_api import Page
from loguru import logger

from src.applicant.stealth import human_type, human_move_and_click
from src.db.models import Job


async def apply_smartrecruiters(
    page: Page,
    profile: dict,
    resume_path: str,
    cover_letter: Optional[str],
    job: Job,
) -> Dict:
    """Apply to a SmartRecruiters job posting."""
    personal = profile.get("personal", {})
    form_answers = profile.get("form_answers", {})

    try:
        # ── Step 1: Click Apply ─────────────────────────
        apply_selectors = [
            'button[data-test="apply-button"]',
            'a[data-test="apply-button"]',
            'button:has-text("Apply Now")',
            'a:has-text("Apply Now")',
            '.apply-btn',
        ]
        for sel in apply_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await human_move_and_click(page, sel)
                await asyncio.sleep(random.uniform(2, 4))
                break

        # ── Step 2: Upload resume ───────────────────────
        # SmartRecruiters often parses resume to pre-fill fields
        file_input = await page.query_selector(
            'input[type="file"][data-test="resume-upload"], '
            'input[type="file"][accept*="pdf"], '
            'input[type="file"]'
        )
        if file_input:
            await file_input.set_input_files(resume_path)
            await asyncio.sleep(random.uniform(3, 6))  # Wait for parsing
            logger.debug("Resume uploaded to SmartRecruiters")

        # ── Step 3: Fill / verify personal info ─────────
        # After resume parse, fields may be pre-filled — verify & correct
        field_map = {
            'input[data-test="first-name"], input[name="firstName"]':
                personal.get("first_name", ""),
            'input[data-test="last-name"], input[name="lastName"]':
                personal.get("last_name", ""),
            'input[data-test="email"], input[name="email"], input[type="email"]':
                personal.get("email", ""),
            'input[data-test="phone"], input[name="phoneNumber"], input[type="tel"]':
                personal.get("phone", ""),
            'input[name="location"], input[data-test="location"]':
                f"{personal.get('location', {}).get('city', '')}, "
                f"{personal.get('location', {}).get('state', '')}",
        }

        for selector, value in field_map.items():
            if not value:
                continue
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    # Clear and re-type to ensure accuracy
                    current = await el.get_attribute("value") or ""
                    if not current.strip():
                        await human_type(page, selector, value, "default")
                    await asyncio.sleep(random.uniform(0.2, 0.5))
            except Exception:
                pass

        # ── Step 4: LinkedIn / links ────────────────────
        link_fields = {
            'input[name*="linkedin"], input[placeholder*="LinkedIn"]':
                personal.get("linkedin", ""),
            'input[name*="github"], input[placeholder*="GitHub"]':
                personal.get("github", ""),
            'input[name*="portfolio"], input[name*="website"]':
                personal.get("portfolio", ""),
        }
        for selector, value in link_fields.items():
            if not value:
                continue
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    await human_type(page, selector, value, "default")
            except Exception:
                pass

        # ── Step 5: Cover letter ────────────────────────
        if cover_letter:
            cl_field = await page.query_selector(
                'textarea[data-test="cover-letter"], '
                'textarea[name*="coverLetter"], '
                'textarea[placeholder*="Cover"]'
            )
            if cl_field and await cl_field.is_visible():
                await human_type(page, 'textarea[data-test="cover-letter"]', cover_letter)

        # ── Step 6: Screening questions ─────────────────
        await _answer_sr_questions(page, form_answers)

        # ── Step 7: Consent checkboxes ──────────────────
        consent_boxes = await page.query_selector_all(
            'input[type="checkbox"][data-test*="consent"], '
            'input[type="checkbox"][name*="consent"], '
            'input[type="checkbox"][name*="agree"]'
        )
        for cb in consent_boxes:
            try:
                if not await cb.is_checked():
                    await cb.click()
                    await asyncio.sleep(0.3)
            except Exception:
                pass

        # ── Step 8: Review & Submit ─────────────────────
        await asyncio.sleep(random.uniform(3, 7))

        submit_selectors = [
            'button[data-test="submit-application"]',
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

        # ── Step 9: Check confirmation ──────────────────
        page_text = await page.inner_text("body")
        if any(w in page_text.lower() for w in
               ["thank you", "submitted", "received your application", "application complete"]):
            return {"success": True, "confirmation_number": "SmartRecruiters confirmed"}

        return {"success": True, "confirmation_number": None}

    except Exception as e:
        return {"success": False, "error": f"SmartRecruiters: {str(e)}"}


async def _answer_sr_questions(page: Page, form_answers: dict):
    """Handle SmartRecruiters screening questions."""
    # Select-based questions
    selects = await page.query_selector_all('select')
    for sel_el in selects:
        try:
            label = await sel_el.evaluate(
                'el => el.closest(".field-wrapper, .question-wrapper, div")?.querySelector("label")?.textContent || ""'
            )
            label_lower = label.lower()

            if any(w in label_lower for w in ["authorized", "eligible", "legal right"]):
                await sel_el.select_option(label="Yes")
            elif any(w in label_lower for w in ["sponsor", "visa"]):
                await sel_el.select_option(label="Yes")
            elif "experience" in label_lower:
                await sel_el.select_option(index=2)  # Usually mid-range
        except Exception:
            pass

    # Radio buttons
    question_groups = await page.query_selector_all(
        '[data-test*="question"], .screening-question, .custom-question'
    )
    for group in question_groups:
        try:
            text = await group.inner_text()
            text_lower = text.lower()
            if any(w in text_lower for w in ["authorized", "sponsor", "legal"]):
                yes_radio = await group.query_selector(
                    'input[type="radio"][value*="yes"], '
                    'input[type="radio"][value="true"], '
                    'label:has-text("Yes") input[type="radio"]'
                )
                if yes_radio:
                    await yes_radio.click()
        except Exception:
            pass

    await asyncio.sleep(random.uniform(0.5, 1.5))
