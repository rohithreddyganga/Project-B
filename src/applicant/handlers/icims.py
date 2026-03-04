"""
iCIMS ATS handler.
iCIMS forms: careers-{company}.icims.com or {company}.icims.com
Large enterprise ATS — used by ~4,000 companies.

Key patterns: iframe-based forms, multi-step, unique field naming.
"""
import asyncio
import random
from typing import Dict, Optional

from playwright.async_api import Page, Frame
from loguru import logger

from src.applicant.stealth import human_type, human_move_and_click
from src.db.models import Job


async def apply_icims(
    page: Page,
    profile: dict,
    resume_path: str,
    cover_letter: Optional[str],
    job: Job,
) -> Dict:
    """Apply to an iCIMS job posting."""
    personal = profile.get("personal", {})
    form_answers = profile.get("form_answers", {})

    try:
        # ── Step 1: Find and click Apply ────────────────
        apply_selectors = [
            'a.iCIMS_PrimaryButton:has-text("Apply")',
            'a[title*="Apply"]',
            'a:has-text("Apply Now")',
            'a:has-text("Apply for this job")',
            'button:has-text("Apply")',
            '.iCIMS_ApplyOnline a',
        ]
        for sel in apply_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await human_move_and_click(page, sel)
                await asyncio.sleep(random.uniform(3, 5))
                break

        # ── Step 2: Handle iframes ──────────────────────
        # iCIMS often renders the form inside an iframe
        form_context = await _get_form_context(page)

        # ── Step 3: Upload resume (usually first step) ──
        file_input = await form_context.query_selector(
            'input[type="file"][name*="resume"], '
            'input[type="file"][name*="Resume"], '
            'input[type="file"][id*="resume"], '
            'input[type="file"]'
        )
        if file_input:
            await file_input.set_input_files(resume_path)
            await asyncio.sleep(random.uniform(2, 4))
            logger.debug("Resume uploaded to iCIMS form")

        # ── Step 4: Fill personal info ──────────────────
        fields = {
            'input[name*="FirstName"], input[id*="firstName"], input[aria-label*="First"]':
                personal.get("first_name", ""),
            'input[name*="LastName"], input[id*="lastName"], input[aria-label*="Last"]':
                personal.get("last_name", ""),
            'input[name*="Email"], input[id*="email"], input[type="email"]':
                personal.get("email", ""),
            'input[name*="Phone"], input[id*="phone"], input[type="tel"]':
                personal.get("phone", ""),
            'input[name*="Address"], input[id*="address"]':
                personal.get("location", {}).get("address", ""),
            'input[name*="City"], input[id*="city"]':
                personal.get("location", {}).get("city", ""),
            'input[name*="Zip"], input[name*="Postal"]':
                personal.get("location", {}).get("zip", ""),
            'input[name*="LinkedIn"], input[id*="linkedin"]':
                personal.get("linkedin", ""),
        }

        for selector, value in fields.items():
            if not value:
                continue
            try:
                el = await form_context.query_selector(selector)
                if el and await el.is_visible():
                    await human_type(form_context, selector, value, "default")
                    await asyncio.sleep(random.uniform(0.3, 0.8))
            except Exception:
                pass

        # ── Step 5: Handle dropdowns ────────────────────
        # State dropdown
        state = personal.get("location", {}).get("state", "")
        if state:
            state_sel = await form_context.query_selector(
                'select[name*="State"], select[id*="state"]'
            )
            if state_sel:
                try:
                    await state_sel.select_option(label=state)
                except Exception:
                    try:
                        await state_sel.select_option(value=state)
                    except Exception:
                        pass

        # ── Step 6: Answer screening questions ──────────
        await _answer_icims_questions(form_context, form_answers)

        # ── Step 7: Cover letter ────────────────────────
        if cover_letter:
            cl_field = await form_context.query_selector(
                'textarea[name*="cover"], textarea[name*="Cover"], '
                'textarea[id*="coverLetter"]'
            )
            if cl_field and await cl_field.is_visible():
                await human_type(form_context, 'textarea[name*="cover"]', cover_letter)

        # ── Step 8: Navigate through pages ──────────────
        for _ in range(4):
            next_btn = await form_context.query_selector(
                'input[type="submit"][value*="Next"], '
                'button:has-text("Next"), '
                'button:has-text("Continue"), '
                'a.iCIMS_PrimaryButton:has-text("Next")'
            )
            if next_btn and await next_btn.is_visible():
                await next_btn.click()
                await asyncio.sleep(random.uniform(2, 4))
                # Re-acquire form context (page may have reloaded)
                form_context = await _get_form_context(page)
                # Fill any new fields on this page
                await _fill_visible_fields(form_context, personal)
            else:
                break

        # ── Step 9: Review pause & Submit ───────────────
        await asyncio.sleep(random.uniform(4, 8))

        submit_selectors = [
            'input[type="submit"][value*="Submit"], '
            'button:has-text("Submit Application")',
            'button:has-text("Submit")',
            'a.iCIMS_PrimaryButton:has-text("Submit")',
            'input[type="submit"]',
        ]
        for sel in submit_selectors:
            btn = await form_context.query_selector(sel)
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(random.uniform(4, 8))
                break

        # ── Step 10: Check confirmation ─────────────────
        page_text = await page.inner_text("body")
        if any(w in page_text.lower() for w in ["thank", "submitted", "received", "confirmation"]):
            return {"success": True, "confirmation_number": "iCIMS submission confirmed"}

        return {"success": True, "confirmation_number": None}

    except Exception as e:
        return {"success": False, "error": f"iCIMS: {str(e)}"}


async def _get_form_context(page: Page):
    """Get the form context — either main page or iframe."""
    # Check for iCIMS iframe
    iframes = page.frames
    for frame in iframes:
        if "icims" in frame.url.lower():
            return frame

    # Also check for generic application iframe
    iframe_el = await page.query_selector('iframe[id*="icims"], iframe[src*="icims"]')
    if iframe_el:
        return await iframe_el.content_frame()

    return page  # No iframe, form is on main page


async def _answer_icims_questions(form_context, form_answers: dict):
    """Handle iCIMS screening questions."""
    # Work authorization
    for sel in [
        'select:has(option:has-text("authorized"))',
        'select[name*="auth"], select[id*="auth"]',
    ]:
        try:
            el = await form_context.query_selector(sel)
            if el and await el.is_visible():
                await el.select_option(label="Yes")
                break
        except Exception:
            pass

    # Sponsorship
    for sel in [
        'select:has(option:has-text("sponsor"))',
        'select[name*="sponsor"], select[id*="visa"]',
    ]:
        try:
            el = await form_context.query_selector(sel)
            if el and await el.is_visible():
                await el.select_option(label="Yes")
                break
        except Exception:
            pass

    # Radio buttons for Yes/No questions
    radios = await form_context.query_selector_all('input[type="radio"]')
    for radio in radios:
        try:
            label_el = await radio.evaluate(
                'el => el.closest("label")?.textContent || '
                'document.querySelector(`label[for="${el.id}"]`)?.textContent || ""'
            )
            parent_text = await radio.evaluate(
                'el => el.closest("div, fieldset, tr")?.textContent || ""'
            )
            # Auto-answer sponsorship / authorization questions with "Yes"
            if any(w in parent_text.lower() for w in ["authorized", "sponsor", "legal right"]):
                value = await radio.get_attribute("value")
                if value and value.lower() in ["yes", "true", "1"]:
                    await radio.click()
                    await asyncio.sleep(0.3)
        except Exception:
            pass

    await asyncio.sleep(random.uniform(0.5, 1.5))


async def _fill_visible_fields(form_context, personal: dict):
    """Quick pass to fill any visible text inputs."""
    inputs = await form_context.query_selector_all(
        'input[type="text"]:not([readonly]), '
        'input[type="email"]:not([readonly]), '
        'input[type="tel"]:not([readonly])'
    )
    for inp in inputs:
        try:
            current_val = await inp.get_attribute("value")
            if current_val:
                continue  # Already filled
            name = (await inp.get_attribute("name") or "").lower()
            placeholder = (await inp.get_attribute("placeholder") or "").lower()
            label = name + " " + placeholder

            if "email" in label:
                await inp.fill(personal.get("email", ""))
            elif "phone" in label or "tel" in label:
                await inp.fill(personal.get("phone", ""))
        except Exception:
            pass
