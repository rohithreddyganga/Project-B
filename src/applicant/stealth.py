"""
Browser stealth and human biometrics simulation.
Makes Playwright browser indistinguishable from a real user.
"""
import asyncio
import random
import math
from typing import List, Tuple

from playwright.async_api import Page, BrowserContext
from loguru import logger

from src.config import config


# ── Stealth patches ──────────────────────────────────────

STEALTH_JS = """
// Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Mock plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' },
        ];
        plugins.length = 3;
        return plugins;
    }
});

// Mock languages
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

// Fix Chrome object
window.chrome = {
    runtime: { id: undefined },
    loadTimes: function() {},
    csi: function() {},
    app: { isInstalled: false },
};

// Fix permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// WebGL vendor/renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.apply(this, arguments);
};

// Connection type
Object.defineProperty(navigator, 'connection', {
    get: () => ({ effectiveType: '4g', rtt: 50, downlink: 10, saveData: false })
});

// Hardware concurrency
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

// Device memory
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
"""


async def apply_stealth(context: BrowserContext):
    """Apply stealth patches to browser context."""
    await context.add_init_script(STEALTH_JS)
    logger.debug("Stealth patches applied to browser context")


# ── Human Biometrics ─────────────────────────────────────

def bezier_curve(
    start: Tuple[float, float],
    end: Tuple[float, float],
    steps: int = 25,
) -> List[Tuple[float, float]]:
    """Generate Bézier curve points for natural mouse movement."""
    # Random control points for natural curve
    cp1 = (
        start[0] + (end[0] - start[0]) * random.uniform(0.2, 0.4) + random.gauss(0, 20),
        start[1] + (end[1] - start[1]) * random.uniform(0.1, 0.3) + random.gauss(0, 20),
    )
    cp2 = (
        start[0] + (end[0] - start[0]) * random.uniform(0.6, 0.8) + random.gauss(0, 15),
        start[1] + (end[1] - start[1]) * random.uniform(0.7, 0.9) + random.gauss(0, 15),
    )

    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = (u**3 * start[0] + 3 * u**2 * t * cp1[0] +
             3 * u * t**2 * cp2[0] + t**3 * end[0])
        y = (u**3 * start[1] + 3 * u**2 * t * cp1[1] +
             3 * u * t**2 * cp2[1] + t**3 * end[1])
        # Add micro-tremor
        x += random.gauss(0, 0.5)
        y += random.gauss(0, 0.5)
        points.append((x, y))

    # 15% chance of overshoot and correction
    stealth_cfg = config.stealth_config
    if random.random() < stealth_cfg.get("mouse_overshoot_probability", 0.15):
        overshoot_x = end[0] + random.uniform(3, 12) * random.choice([-1, 1])
        overshoot_y = end[1] + random.uniform(2, 8) * random.choice([-1, 1])
        points.append((overshoot_x, overshoot_y))
        # Correction back
        for i in range(3):
            t = (i + 1) / 3
            x = overshoot_x + (end[0] - overshoot_x) * t
            y = overshoot_y + (end[1] - overshoot_y) * t
            points.append((x + random.gauss(0, 0.3), y + random.gauss(0, 0.3)))

    return points


async def human_move_and_click(page: Page, selector: str):
    """Move mouse naturally to element and click."""
    try:
        element = await page.wait_for_selector(selector, timeout=10000)
        if not element:
            return
        box = await element.bounding_box()
        if not box:
            await element.click()
            return

        # Current mouse position (approximate)
        start = (random.uniform(100, 500), random.uniform(100, 400))
        end = (
            box["x"] + box["width"] * random.uniform(0.3, 0.7),
            box["y"] + box["height"] * random.uniform(0.3, 0.7),
        )

        # Move along Bézier curve
        points = bezier_curve(start, end)
        for x, y in points:
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.005, 0.02))

        # Small pause before click
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.click(end[0], end[1])

    except Exception as e:
        # Fallback: direct click
        logger.debug(f"Human click fallback: {e}")
        try:
            await page.click(selector)
        except Exception:
            pass


async def human_type(page: Page, selector: str, text: str, field_type: str = "default"):
    """Type text with human-like speed and occasional typos."""
    stealth_cfg = config.stealth_config
    speeds = stealth_cfg.get("typing_speed_wpm", {})
    wpm = speeds.get(field_type, speeds.get("default", 45))

    # Convert WPM to delay between keystrokes
    chars_per_min = wpm * 5  # Average word = 5 chars
    base_delay = 60.0 / chars_per_min
    typo_rate = stealth_cfg.get("typo_rate", 0.02)

    await human_move_and_click(page, selector)
    await asyncio.sleep(random.uniform(0.2, 0.5))

    for char in text:
        # Occasional typo
        if random.random() < typo_rate:
            wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            await page.keyboard.type(wrong_char, delay=base_delay * 1000 * random.uniform(0.7, 1.3))
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.05, 0.15))

        delay = base_delay * random.uniform(0.6, 1.5) * 1000  # ms
        await page.keyboard.type(char, delay=delay)

    # Small pause after typing
    await asyncio.sleep(random.uniform(0.2, 0.6))


async def human_scroll_read(page: Page, pause_min: float = 1.5, pause_max: float = 4.5):
    """Simulate reading a page by scrolling naturally."""
    stealth_cfg = config.stealth_config
    p_min = stealth_cfg.get("scroll_pause_min", pause_min)
    p_max = stealth_cfg.get("scroll_pause_max", pause_max)

    viewport_height = page.viewport_size.get("height", 900) if page.viewport_size else 900
    scroll_amount = viewport_height * random.uniform(0.6, 0.9)

    # Scroll down in chunks
    for _ in range(random.randint(2, 5)):
        await page.mouse.wheel(0, scroll_amount * random.uniform(0.5, 1.2))
        await asyncio.sleep(random.uniform(p_min, p_max))

    # Sometimes scroll back up a bit
    if random.random() < 0.3:
        await page.mouse.wheel(0, -scroll_amount * 0.3)
        await asyncio.sleep(random.uniform(0.5, 1.5))
