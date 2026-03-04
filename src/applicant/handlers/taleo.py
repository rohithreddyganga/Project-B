"""
Taleo ATS handler (Oracle Recruiting Cloud).
URLs: *taleo.net, oracle.com/careers
Legacy enterprise ATS — slow, Java-heavy, often uses iframes.

Known quirks: heavy page loads, session timeouts, legacy HTML.
"""
import asyncio
import random
from typing import Dict, Optional

from playwright.async_api import Page
from loguru import logger

from src.applicant.stealth import human_type, human_move_and_click
from src.db.models import Job


async def apply_taleo(
    page: Page,
    profile: dict,
    resume_path: str,
    cover_letter: Optional[str],
    job: Job,
) -> Dict:
    """Apply to a Taleo/Oracle job posting."""
    personal = profile.get("personal", {})
    form_answers = profile.get("form_answers", {})

    try:
        # Taleo pages load slowly — give extra time
        await page.wait_for_load_state("networkidle", timeout=15000)

        # ── Step 1: Click Apply ─────────────────────────
        apply_selectors = [
            'a[id*="apply"], a[id*="Apply"]',
            'input[value*="Apply"], input[value*="APPLY"]',
            'a:has-text("Apply Online")',
            'a:has-text("Apply Now")',
            'a:has-text("Apply for this job")',
            'button:has-text("Apply")',
            '#applyButton',
        ]
        for sel in apply_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await human_move_and_click(page, sel)
                await asyncio.sleep(random.uniform(4, 7))  # Taleo is slow
                break

        # Handle potential login/signup page
        # Try to find "New User" or "Apply Without Account" option
        guest_selectors = [
            'a:has-text("New User")',
            'a:has-text("Guest")',
            'a:has-text("Apply without")',
            'input[value*="New User"]',
            'a:has-text("Create Account")',
        ]
        for sel in guest_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(random.uniform(3, 5))
                break

        # ── Step 2: Upload Resume ───────────────────────
        file_input = await page.query_selector(
            'input[type="file"][name*="resume"], '
            'input[type="file"][name*="Resume"], '
            'input[type="file"][id*="attach"], '
            'input[type="file"]'
        )
        if file_input:
            await file_input.set_input_files(resume_path)
            await asyncio.sleep(random.uniform(3, 6))
            logger.debug("Resume uploaded to Taleo form")

        # ── Step 3: Fill personal fields ────────────────
        # Taleo uses both standard HTML and custom naming
        field_map = {
            'input[id*="FirstName"], input[name*="FirstName"]':
                personal.get("first_name", ""),
            'input[id*="LastName"], input[name*="LastName"]':
                personal.get("last_name", ""),
            'input[id*="Email"], input[name*="Email"], input[type="email"]':
                personal.get("email", ""),
            'input[id*="Phone"], input[name*="Phone"], input[type="tel"]':
                personal.get("phone", ""),
            'input[id*="Address"], input[name*="Address"]':
                personal.get("location", {}).get("address", ""),
            'input[id*="City"], input[name*="City"]':
                personal.get("location", {}).get("city", ""),
            'input[id*="ZipCode"], input[name*="Zip"]':
                personal.get("location", {}).get("zip", ""),
        }

        for selector, value in field_map.items():
            if not value:
                continue
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    await human_type(page, selector, value, "default")
                    await asyncio.sleep(random.uniform(0.4, 1.0))
            except Exception:
                pass

        # State dropdown
        state = personal.get("location", {}).get("state", "")
        if state:
            for sel in ['select[id*="State"]', 'select[name*="State"]', 'select[id*="region"]']:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        await el.select_option(label=state)
                        break
                except Exception:
                    continue

        # ── Step 4: Screening questions ─────────────────
        await _answer_taleo_questions(page, form_answers)

        # ── Step 5: Navigate wizard pages ───────────────
        for _ in range(5):
            await asyncio.sleep(random.uniform(2, 4))

            next_selectors = [
                'input[value*="Next"], input[value*="NEXT"]',
                'a:has-text("Next")',
                'button:has-text("Next")',
                'input[value*="Save and Continue"]',
                'input[value*="Continue"]',
            ]
            clicked = False
            for sel in next_selectors:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(random.uniform(3, 6))
                    clicked = True
                    break
            if not clicked:
                break

            # Fill any new fields on the new page
            await _fill_taleo_page_fields(page, personal, form_answers)

        # ── Step 6: Submit ──────────────────────────────
        await asyncio.sleep(random.uniform(3, 7))

        submit_selectors = [
            'input[value*="Submit"], input[value*="SUBMIT"]',
            'button:has-text("Submit Application")',
            'button:has-text("Submit")',
            'a:has-text("Submit")',
            'input[type="submit"]',
        ]
        for sel in submit_selectors:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                await btn.click()
                await asyncio.sleep(random.uniform(5, 10))
                break

        # ── Step 7: Check confirmation ──────────────────
        page_text = await page.inner_text("body")
        if any(w in page_text.lower() for w in
               ["thank you", "submitted", "received", "confirmation", "application has been"]):
            return {"success": True, "confirmation_number": "Taleo submission confirmed"}

        return {"success": True, "confirmation_number": None}

    except Exception as e:
        return {"success": False, "error": f"Taleo: {str(e)}"}


async def _answer_taleo_questions(page: Page, form_answers: dict):
    """Handle Taleo screening questions — often radio buttons or selects."""
    # Taleo uses table-based layouts for questions
    rows = await page.query_selector_all('tr:has(select), tr:has(input[type="radio"])')

    for row in rows:
        try:
            text = await row.inner_text()
            text_lower = text.lower()

            # Work authorization
            if any(w in text_lower for w in ["authorized to work", "eligible to work", "legal right"]):
                yes_sel = await row.query_selector('select')
                if yes_sel:
                    await yes_sel.select_option(label="Yes")
                else:
                    yes_radio = await row.query_selector(
                        'input[type="radio"][value*="Yes"], '
                        'input[type="radio"][value="1"]'
                    )
                    if yes_radio:
                        await yes_radio.click()

            # Sponsorship
            elif any(w in text_lower for w in ["sponsorship", "sponsor", "visa"]):
                sel = await row.query_selector('select')
                if sel:
                    await sel.select_option(label="Yes")
                else:
                    yes_radio = await row.query_selector(
                        'input[type="radio"][value*="Yes"], '
                        'input[type="radio"][value="1"]'
                    )
                    if yes_radio:
                        await yes_radio.click()
        except Exception:
            pass

    await asyncio.sleep(random.uniform(0.5, 1.5))


async def _fill_taleo_page_fields(page: Page, personal: dict, form_answers: dict):
    """Fill fields on the current Taleo wizard page."""
    # Re-try filling any empty required fields
    required_fields = await page.query_selector_all(
        'input[required]:not([readonly]), input.required:not([readonly])'
    )
    for field in required_fields:
        try:
            value = await field.get_attribute("value")
            if value:
                continue  # Already filled

            name = (await field.get_attribute("name") or "").lower()
            ftype = (await field.get_attribute("type") or "text").lower()

            if ftype == "email":
                await field.fill(personal.get("email", ""))
            elif "phone" in name:
                await field.fill(personal.get("phone", ""))
        except Exception:
            pass

    # Answer any new screening questions
    await _answer_taleo_questions(page, form_answers)
