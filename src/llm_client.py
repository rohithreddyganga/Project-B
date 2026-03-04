"""
Claude API client wrapper with automatic cost tracking.
All AI calls in the system go through this module.
"""
import logging
import json
from datetime import datetime
from typing import Optional

import anthropic

from src.config import config

logger = logging.getLogger(__name__)

# ── Pricing (per 1M tokens) ────────────────────────
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
}

# ── Client singleton ───────────────────────────────
_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.env.ANTHROPIC_API_KEY)
    return _client


# ── Cost accumulator (flushed to DB periodically) ──
_cost_buffer: list[dict] = []


def get_cost_buffer() -> list[dict]:
    """Return and clear the cost buffer."""
    global _cost_buffer
    buf = _cost_buffer.copy()
    _cost_buffer = []
    return buf


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a call."""
    prices = PRICING.get(model, {"input": 3.0, "output": 15.0})
    return (input_tokens * prices["input"] / 1_000_000) + \
           (output_tokens * prices["output"] / 1_000_000)


# ── Main call functions ─────────────────────────────

async def call_haiku(
    prompt: str,
    system: str = "",
    max_tokens: int = 0,
    temperature: float = 0.0,
    operation: str = "generic",
    application_id: str = None,
) -> str:
    """Call Claude Haiku (cheap, fast — scoring/classification)."""
    return await _call_model(
        model=config.ai.scoring_model,
        prompt=prompt,
        system=system,
        max_tokens=max_tokens or config.ai.max_tokens_scoring,
        temperature=temperature or config.ai.temperature_scoring,
        operation=operation,
        application_id=application_id,
    )


async def call_sonnet(
    prompt: str,
    system: str = "",
    max_tokens: int = 0,
    temperature: float = 0.0,
    operation: str = "generic",
    application_id: str = None,
) -> str:
    """Call Claude Sonnet (premium — resume writing/cover letters)."""
    return await _call_model(
        model=config.ai.writing_model,
        prompt=prompt,
        system=system,
        max_tokens=max_tokens or config.ai.max_tokens_writing,
        temperature=temperature or config.ai.temperature_writing,
        operation=operation,
        application_id=application_id,
    )


async def _call_model(
    model: str,
    prompt: str,
    system: str,
    max_tokens: int,
    temperature: float,
    operation: str,
    application_id: str = None,
) -> str:
    """Internal: make the API call with cost tracking."""
    client = get_client()

    try:
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)

        # Extract text
        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        # Track cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = _calculate_cost(model, input_tokens, output_tokens)

        _cost_buffer.append({
            "timestamp": datetime.utcnow().isoformat(),
            "service": model.split("-")[1],  # "haiku" or "sonnet"
            "operation": operation,
            "application_id": application_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
        })

        logger.debug(f"LLM call: {model} | {operation} | {input_tokens}+{output_tokens} tokens | ${cost:.4f}")
        return text

    except Exception as e:
        logger.error(f"LLM call failed ({model}, {operation}): {e}")
        raise


async def call_haiku_json(
    prompt: str,
    system: str = "",
    operation: str = "generic",
    application_id: str = None,
) -> dict:
    """Call Haiku and parse response as JSON."""
    system_full = (system or "") + "\n\nRespond ONLY with valid JSON. No markdown, no backticks, no explanation."
    text = await call_haiku(prompt, system=system_full, operation=operation, application_id=application_id)
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    return json.loads(text)
