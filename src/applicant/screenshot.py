"""
Screenshot capture + confirmation ID extraction.
Takes full-page screenshot after submission, uses Claude Haiku vision to find confirmation number.
"""
import logging
from typing import Optional, Tuple

from playwright.async_api import Page

from src import llm_client

logger = logging.getLogger(__name__)


async def capture_screenshot(page: Page) -> Optional[bytes]:
    """Take full-page screenshot as PNG bytes."""
    try:
        png_bytes = await page.screenshot(full_page=True, type="png")
        logger.info(f"Screenshot captured: {len(png_bytes)} bytes")
        return png_bytes
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return None


async def extract_confirmation(page: Page, application_id: str = None) -> Optional[str]:
    """
    Extract confirmation/application ID from the current page.
    Uses page text analysis first, then falls back to visual analysis.
    """
    try:
        # Try text extraction first (cheaper than vision)
        text = await page.inner_text("body")
        text_lower = text.lower()

        # Common confirmation patterns
        import re
        patterns = [
            r'confirmation\s*(?:number|id|#|code)?\s*:?\s*([A-Z0-9-]{4,20})',
            r'application\s*(?:number|id|#)?\s*:?\s*([A-Z0-9-]{4,20})',
            r'reference\s*(?:number|id|#)?\s*:?\s*([A-Z0-9-]{4,20})',
            r'tracking\s*(?:number|id|#)?\s*:?\s*([A-Z0-9-]{4,20})',
            r'(?:id|number|ref)\s*:?\s*#?\s*([A-Z0-9-]{4,20})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                conf_id = match.group(1)
                logger.info(f"Confirmation found via text: {conf_id}")
                return conf_id

        # Check for success indicators without explicit ID
        success_phrases = [
            "application submitted",
            "thank you for applying",
            "application received",
            "successfully submitted",
            "we have received your application",
        ]
        for phrase in success_phrases:
            if phrase in text_lower:
                logger.info(f"Submission confirmed (no ID): '{phrase}'")
                return f"CONFIRMED-{phrase[:20].replace(' ', '_').upper()}"

        logger.warning("Could not extract confirmation from page")
        return None

    except Exception as e:
        logger.error(f"Confirmation extraction failed: {e}")
        return None
