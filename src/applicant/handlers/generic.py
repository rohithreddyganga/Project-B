"""
Generic application handler — AI-powered fallback for unknown portals.
Uses Claude Haiku to analyze form structure and fill intelligently.
"""
import asyncio
import random
from typing import Dict, Optional

import anthropic
from playwright.async_api import Page
from loguru import logger

from src.config import config
from src.applicant.stealth import human_type, human_move_and_click
from src.db.models import Job


async def apply_generic(
    page: Page,
    profile: dict,
    resume_path: str,
    cover_letter: Optional[str],
    job: Job,
) -> Dict:
    """
    Generic form filler for unknown ATS platforms.
    Strategy: Extract all form fields → use LLM to map profile data → fill.
    """
    personal = profile.get("personal", {})
    form_answers = profile.get("form_answers", {})

    try:
        # Step 1: Find all input fields on the page
        fields = await _extract_form_fields(page)
        if not fields:
            return {"success": False, "error": "No form fields found"}

        logger.debug(f"Generic handler: found {len(fields)} form fields")

        # Step 2: Use LLM to map fields to profile data
        field_mapping = await _map_fields_with_llm(fields, personal, form_answers)

        # Step 3: Fill each mapped field
        for field_info in field_mapping:
            selector = field_info.get("selector", "")
            value = field_info.get("value", "")
            field_type = field_info.get("type", "text")

            if not value or not selector:
                continue

            try:
                if field_type == "file":
                    file_input = await page.query_selector(selector)
                    if file_input:
                        await file_input.set_input_files(resume_path)
                        await asyncio.sleep(random.uniform(1, 2))
                elif field_type == "select":
                    el = await page.query_selector(selector)
                    if el:
                        await el.select_option(label=value)
                elif field_type == "textarea":
                    await human_type(page, selector, value, "default")
                elif field_type == "radio" or field_type == "checkbox":
                    await page.click(selector)
                else:
                    await human_type(page, selector, value, "default")

                await asyncio.sleep(random.uniform(0.3, 1.0))
            except Exception as e:
                logger.debug(f"Field fill error ({selector}): {e}")

        # Step 4: Upload resume (try common file input selectors)
        for sel in ['input[type="file"][name*="resume"]', 'input[type="file"][name*="cv"]',
                     'input[type="file"]:first-of-type']:
            try:
                file_input = await page.query_selector(sel)
                if file_input:
                    await file_input.set_input_files(resume_path)
                    await asyncio.sleep(random.uniform(1, 2))
                    break
            except Exception:
                continue

        # Step 5: Fill cover letter if available
        if cover_letter:
            for sel in ['textarea[name*="cover"]', 'textarea[name*="letter"]',
                         'textarea[name*="message"]']:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await human_type(page, sel, cover_letter)
                        break
                except Exception:
                    continue

        # Step 6: Review pause
        await asyncio.sleep(random.uniform(5, 10))

        # Step 7: Submit
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
            'a:has-text("Submit Application")',
        ]
        for sel in submit_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await human_move_and_click(page, sel)
                    await asyncio.sleep(random.uniform(3, 6))
                    break
            except Exception:
                continue

        # Check for success
        page_text = await page.inner_text("body")
        success_words = ["thank", "submitted", "received", "confirmation", "success"]
        if any(w in page_text.lower() for w in success_words):
            return {"success": True, "confirmation_number": "Generic submission confirmed"}

        return {"success": True, "confirmation_number": None}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _extract_form_fields(page: Page) -> list:
    """Extract all visible form fields from the page."""
    fields = await page.evaluate("""
    () => {
        const fields = [];
        const inputs = document.querySelectorAll('input, select, textarea');
        for (const el of inputs) {
            if (el.offsetParent === null) continue;  // Skip hidden
            if (el.type === 'hidden') continue;

            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;

            fields.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || 'text',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                label: (() => {
                    const label = el.closest('label') ||
                                  document.querySelector(`label[for="${el.id}"]`);
                    return label ? label.textContent.trim() : '';
                })(),
                required: el.required,
                selector: el.id ? `#${el.id}` :
                          el.name ? `[name="${el.name}"]` :
                          null,
            });
        }
        return fields;
    }
    """)
    return [f for f in fields if f.get("selector")]


async def _map_fields_with_llm(fields: list, personal: dict, form_answers: dict) -> list:
    """Use Claude to map form fields to profile data."""
    api_key = config.env.anthropic_api_key

    # First try rule-based mapping (faster, cheaper)
    mapped = _rule_based_mapping(fields, personal, form_answers)

    # If most fields are mapped, skip LLM
    mapped_count = sum(1 for f in mapped if f.get("value"))
    if mapped_count >= len(fields) * 0.7:
        return mapped

    if not api_key:
        return mapped

    # LLM mapping for remaining unmapped fields
    unmapped = [f for f in mapped if not f.get("value")]
    if not unmapped:
        return mapped

    fields_desc = "\n".join(
        f"- selector={f['selector']}, label='{f.get('label','')}', "
        f"name='{f.get('name','')}', type={f.get('type','text')}"
        for f in unmapped[:20]  # Limit to 20 fields
    )

    profile_summary = f"""
Name: {personal.get('first_name','')} {personal.get('last_name','')}
Email: {personal.get('email','')}
Phone: {personal.get('phone','')}
LinkedIn: {personal.get('linkedin','')}
GitHub: {personal.get('github','')}
Location: {personal.get('location',{}).get('city','')}, {personal.get('location',{}).get('state','')}
Work Auth: Yes (F1-OPT), Requires Sponsorship: Yes
"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=config.llm_config.get("scoring_model", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            temperature=0.1,
            messages=[{"role": "user", "content": f"""Map these form fields to the profile data below.
For each field, respond with: selector|value
If a field shouldn't be filled, skip it.

FORM FIELDS:
{fields_desc}

PROFILE:
{profile_summary}

Respond ONLY with mappings, one per line: selector|value"""}],
        )

        text = response.content[0].text.strip()
        for line in text.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 1)
                selector = parts[0].strip()
                value = parts[1].strip()
                # Find the field in mapped list and update
                for f in mapped:
                    if f.get("selector") == selector:
                        f["value"] = value
                        break
    except Exception as e:
        logger.warning(f"LLM field mapping failed: {e}")

    return mapped


def _rule_based_mapping(fields: list, personal: dict, form_answers: dict) -> list:
    """Fast rule-based field mapping without LLM."""
    result = []
    for field in fields:
        name = (field.get("name", "") + field.get("label", "") + field.get("placeholder", "")).lower()
        value = ""

        if any(w in name for w in ["first_name", "first name", "fname", "given"]):
            value = personal.get("first_name", "")
        elif any(w in name for w in ["last_name", "last name", "lname", "family", "surname"]):
            value = personal.get("last_name", "")
        elif any(w in name for w in ["full_name", "full name", "your name"]):
            value = f"{personal.get('first_name', '')} {personal.get('last_name', '')}"
        elif any(w in name for w in ["email", "e-mail"]):
            value = personal.get("email", "")
        elif any(w in name for w in ["phone", "mobile", "tel"]):
            value = personal.get("phone", "")
        elif any(w in name for w in ["linkedin"]):
            value = personal.get("linkedin", "")
        elif any(w in name for w in ["github"]):
            value = personal.get("github", "")
        elif any(w in name for w in ["website", "portfolio", "url"]):
            value = personal.get("portfolio", "")
        elif any(w in name for w in ["city"]):
            value = personal.get("location", {}).get("city", "")
        elif any(w in name for w in ["state"]):
            value = personal.get("location", {}).get("state", "")
        elif any(w in name for w in ["zip", "postal"]):
            value = personal.get("location", {}).get("zip", "")

        result.append({**field, "value": value})

    return result
