"""
F1-OPT Visa / Sponsorship Filter.
Stage 3 of the pipeline — runs BEFORE any AI spending.
Two-pass approach: fast regex first, Claude Haiku fallback for ambiguous cases.
"""
import re
from typing import Tuple

import anthropic
from loguru import logger

from src.config import config
from src.db.models import VisaStatus


# Compile regex patterns once
_visa_cfg = config.visa_filter_config
_block_patterns = [
    re.compile(re.escape(signal), re.IGNORECASE)
    for signal in _visa_cfg.get("block_signals", [])
]
_allow_patterns = [
    re.compile(re.escape(signal), re.IGNORECASE)
    for signal in _visa_cfg.get("allow_signals", [])
]


def regex_visa_check(jd_text: str) -> Tuple[VisaStatus, str]:
    """
    Fast regex-based visa check. Returns (status, reason).
    - blocked: Contains explicit "no sponsorship" signals
    - ok: Contains explicit "visa sponsorship available" signals
    - unchecked: Ambiguous — needs LLM classification
    """
    if not jd_text:
        return VisaStatus.unchecked, "No JD text available"

    text = jd_text.lower()

    # Check block signals first (higher priority)
    for pattern in _block_patterns:
        match = pattern.search(text)
        if match:
            return VisaStatus.blocked, f"Blocked: '{match.group()}'"

    # Check allow signals
    for pattern in _allow_patterns:
        match = pattern.search(text)
        if match:
            return VisaStatus.ok, f"Allowed: '{match.group()}'"

    # No clear signal → ambiguous
    return VisaStatus.unchecked, "No visa signals found in JD"


async def llm_visa_check(jd_text: str) -> Tuple[VisaStatus, float, str]:
    """
    Claude Haiku classification for ambiguous JDs.
    Returns (status, confidence, reasoning).
    Only called when regex_visa_check returns 'unchecked'.
    """
    api_key = config.env.anthropic_api_key
    if not api_key:
        return VisaStatus.unclear, 0.0, "No API key configured"

    threshold = _visa_cfg.get("llm_confidence_threshold", 0.90)

    prompt = """Analyze this job description for visa sponsorship eligibility.
I am an international student on F1-STEM OPT in the US. I need a company that:
- Does NOT explicitly exclude visa sponsorship
- Is open to hiring F1-OPT workers who may later need H-1B sponsorship

Based on the job description, classify:
- "ok" = The company likely sponsors or is open to international candidates
- "blocked" = The company explicitly or strongly implies they won't sponsor
- "unclear" = Cannot determine from the JD

Respond in this exact format:
STATUS: ok|blocked|unclear
CONFIDENCE: 0.0-1.0
REASON: Brief explanation

Job Description:
"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=config.llm_config.get("scoring_model", "claude-haiku-4-5-20251001"),
            max_tokens=256,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt + jd_text[:3000]}],
        )

        text = response.content[0].text.strip()

        # Parse response
        status_match = re.search(r'STATUS:\s*(ok|blocked|unclear)', text, re.IGNORECASE)
        conf_match = re.search(r'CONFIDENCE:\s*([\d.]+)', text)
        reason_match = re.search(r'REASON:\s*(.+)', text, re.DOTALL)

        status_str = status_match.group(1).lower() if status_match else "unclear"
        confidence = float(conf_match.group(1)) if conf_match else 0.5
        reason = reason_match.group(1).strip() if reason_match else "LLM analysis"

        # Map to VisaStatus
        if confidence < threshold:
            # Below confidence threshold → flag for human review
            return VisaStatus.unclear, confidence, f"Low confidence ({confidence:.0%}): {reason}"

        status_map = {"ok": VisaStatus.ok, "blocked": VisaStatus.blocked}
        final_status = status_map.get(status_str, VisaStatus.unclear)

        return final_status, confidence, reason

    except Exception as e:
        logger.error(f"LLM visa check failed: {e}")
        return VisaStatus.unclear, 0.0, f"LLM error: {str(e)}"


async def check_visa(jd_text: str) -> Tuple[VisaStatus, str]:
    """
    Full visa check pipeline: regex first, LLM fallback.
    Returns (status, reason).
    """
    # Pass 1: Fast regex
    status, reason = regex_visa_check(jd_text)
    if status != VisaStatus.unchecked:
        logger.debug(f"Visa regex: {status.value} — {reason}")
        return status, reason

    # Pass 2: LLM classification for ambiguous cases
    status, confidence, reason = await llm_visa_check(jd_text)
    logger.debug(f"Visa LLM: {status.value} (conf={confidence:.0%}) — {reason}")
    return status, reason
