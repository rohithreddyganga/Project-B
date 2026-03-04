"""
CAPTCHA Solver — integrates with CapSolver API.
Handles reCAPTCHA v2, reCAPTCHA v3, hCaptcha.
"""
import asyncio
import logging
from typing import Optional

import httpx

from src.config import config

logger = logging.getLogger(__name__)

CAPSOLVER_URL = "https://api.capsolver.com"


async def solve_recaptcha_v2(site_key: str, page_url: str) -> Optional[str]:
    """Solve reCAPTCHA v2 and return the token."""
    return await _solve({
        "type": "ReCaptchaV2TaskProxyLess",
        "websiteURL": page_url,
        "websiteKey": site_key,
    })


async def solve_recaptcha_v3(site_key: str, page_url: str, action: str = "submit") -> Optional[str]:
    """Solve reCAPTCHA v3."""
    return await _solve({
        "type": "ReCaptchaV3TaskProxyLess",
        "websiteURL": page_url,
        "websiteKey": site_key,
        "pageAction": action,
        "minScore": 0.7,
    })


async def solve_hcaptcha(site_key: str, page_url: str) -> Optional[str]:
    """Solve hCaptcha."""
    return await _solve({
        "type": "HCaptchaTaskProxyLess",
        "websiteURL": page_url,
        "websiteKey": site_key,
    })


async def _solve(task: dict) -> Optional[str]:
    """Submit task to CapSolver and poll for result."""
    if not config.env.CAPSOLVER_API_KEY:
        logger.warning("No CapSolver API key configured")
        return None

    async with httpx.AsyncClient(timeout=120) as client:
        # Create task
        try:
            resp = await client.post(
                f"{CAPSOLVER_URL}/createTask",
                json={
                    "clientKey": config.env.CAPSOLVER_API_KEY,
                    "task": task,
                },
            )
            data = resp.json()
            if data.get("errorId"):
                logger.error(f"CapSolver create error: {data.get('errorDescription')}")
                return None
            task_id = data.get("taskId")
        except Exception as e:
            logger.error(f"CapSolver request failed: {e}")
            return None

        # Poll for result
        for _ in range(60):  # Max 2 minutes
            await asyncio.sleep(2)
            try:
                resp = await client.post(
                    f"{CAPSOLVER_URL}/getTaskResult",
                    json={
                        "clientKey": config.env.CAPSOLVER_API_KEY,
                        "taskId": task_id,
                    },
                )
                data = resp.json()
                status = data.get("status")

                if status == "ready":
                    token = data.get("solution", {}).get("gRecaptchaResponse") or \
                            data.get("solution", {}).get("token")
                    logger.info("CAPTCHA solved successfully")
                    return token
                elif status == "failed":
                    logger.error(f"CapSolver failed: {data.get('errorDescription')}")
                    return None
            except Exception as e:
                logger.warning(f"CapSolver poll error: {e}")
                continue

    logger.error("CapSolver timed out")
    return None
