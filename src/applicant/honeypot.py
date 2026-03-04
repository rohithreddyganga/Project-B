"""
Honeypot Detector — identifies trap form fields that bots shouldn't fill.
Checks: display:none, visibility:hidden, zero dimensions, off-screen, suspicious names.
"""
import logging
from typing import List

from playwright.async_api import Page, ElementHandle

logger = logging.getLogger(__name__)

TRAP_CLASS_NAMES = {"honeypot", "trap", "bot", "hp-field", "ohnohoney", "winnie"}
TRAP_NAME_PATTERNS = {"honeypot", "trap", "bot_check", "hp_", "phone2", "email2", "address2"}


async def is_honeypot(page: Page, element: ElementHandle) -> bool:
    """Check if a form element is a honeypot trap."""
    try:
        score = 0
        props = await page.evaluate("""(el) => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return {
                display: style.display,
                visibility: style.visibility,
                opacity: parseFloat(style.opacity),
                width: rect.width,
                height: rect.height,
                top: rect.top,
                left: rect.left,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                className: el.className || '',
                tabIndex: el.tabIndex,
                ariaHidden: el.getAttribute('aria-hidden'),
            };
        }""", element)

        # Display checks
        if props["display"] == "none":
            score += 3
        if props["visibility"] == "hidden":
            score += 3
        if props["opacity"] == 0:
            score += 2

        # Dimension checks
        if props["width"] == 0 or props["height"] == 0:
            score += 2

        # Off-screen position
        if props["top"] < -1000 or props["left"] < -1000:
            score += 3

        # Hidden input type
        if props["type"] == "hidden":
            score += 1

        # Suspicious class names
        class_lower = props["className"].lower()
        if any(trap in class_lower for trap in TRAP_CLASS_NAMES):
            score += 3

        # Suspicious name/id
        name_lower = (props["name"] + props["id"]).lower()
        if any(trap in name_lower for trap in TRAP_NAME_PATTERNS):
            score += 3

        # Tab index -1
        if props["tabIndex"] == -1:
            score += 1

        # aria-hidden
        if props["ariaHidden"] == "true":
            score += 2

        is_trap = score >= 4
        if is_trap:
            logger.debug(f"Honeypot detected (score={score}): name={props['name']}, id={props['id']}")
        return is_trap

    except Exception as e:
        logger.warning(f"Honeypot check error: {e}")
        return False


async def filter_visible_fields(page: Page, selector: str = "input, textarea, select") -> List[ElementHandle]:
    """Return only visible, non-honeypot form fields."""
    all_fields = await page.query_selector_all(selector)
    visible = []
    for field in all_fields:
        if not await is_honeypot(page, field):
            visible.append(field)
    return visible
