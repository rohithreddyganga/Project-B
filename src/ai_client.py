"""
Unified AI client for Claude Haiku (scoring/classification) 
and Claude Sonnet (writing/optimization).

Tracks token usage for cost reporting.
"""
import json
import logging
from dataclasses import dataclass
from anthropic import AsyncAnthropic
from src.config import config

logger = logging.getLogger(__name__)

# Model constants
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-5-20250929"

# Pricing per million tokens
PRICING = {
    HAIKU:  {"input": 1.00, "output": 5.00},
    SONNET: {"input": 3.00, "output": 15.00},
}


@dataclass
class AIResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class AIClient:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=config.env.anthropic_api_key)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
    
    async def _call(self, model: str, system: str, user: str,
                    max_tokens: int = 2048, temperature: float = 0.3) -> AIResponse:
        """Make a single API call and track usage."""
        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            
            inp = response.usage.input_tokens
            out = response.usage.output_tokens
            pricing = PRICING[model]
            cost = (inp * pricing["input"] + out * pricing["output"]) / 1_000_000
            
            self.total_input_tokens += inp
            self.total_output_tokens += out
            self.total_cost += cost
            
            text = response.content[0].text if response.content else ""
            
            return AIResponse(
                text=text,
                model=model,
                input_tokens=inp,
                output_tokens=out,
                cost_usd=cost,
            )
        except Exception as e:
            logger.error(f"AI call failed ({model}): {e}")
            raise
    
    async def haiku(self, system: str, user: str, **kwargs) -> AIResponse:
        """Quick/cheap calls: scoring, classification, extraction."""
        return await self._call(HAIKU, system, user, **kwargs)
    
    async def sonnet(self, system: str, user: str, **kwargs) -> AIResponse:
        """Quality calls: resume writing, cover letters."""
        return await self._call(SONNET, system, user, max_tokens=4096, **kwargs)
    
    async def haiku_json(self, system: str, user: str, **kwargs) -> dict:
        """Haiku call that returns parsed JSON."""
        response = await self.haiku(
            system=system + "\n\nRespond ONLY with valid JSON. No markdown, no backticks, no explanation.",
            user=user,
            **kwargs,
        )
        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from Haiku: {response.text[:200]}")
            return {}
    
    def get_usage_stats(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
        }


# Singleton
_client = None

def get_ai_client() -> AIClient:
    global _client
    if _client is None:
        _client = AIClient()
    return _client
