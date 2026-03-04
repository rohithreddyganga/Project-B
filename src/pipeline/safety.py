"""
Safety Guard — rate limiting, backoff, anomaly detection.
Prevents over-application and handles errors gracefully.
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from collections import defaultdict

from src.config import config

logger = logging.getLogger(__name__)

# Track per-platform failures
_platform_failures: dict[str, int] = defaultdict(int)
_daily_count: int = 0
_hourly_count: int = 0
_last_hour_reset: datetime = datetime.utcnow()
_last_day_reset: datetime = datetime.utcnow()


def reset_daily():
    """Reset daily counters (called by scheduler at midnight)."""
    global _daily_count, _platform_failures
    _daily_count = 0
    _platform_failures.clear()
    logger.info("Daily safety counters reset")


def _check_hourly():
    """Reset hourly counter if needed."""
    global _hourly_count, _last_hour_reset
    now = datetime.utcnow()
    if (now - _last_hour_reset).total_seconds() >= 3600:
        _hourly_count = 0
        _last_hour_reset = now


def can_apply() -> tuple[bool, str]:
    """Check if we're allowed to submit another application right now."""
    _check_hourly()

    # Check daily limit
    if _daily_count >= config.pacing.max_apps_per_day:
        return False, f"Daily limit reached ({_daily_count}/{config.pacing.max_apps_per_day})"

    # Check hourly limit
    if _hourly_count >= config.pacing.max_apps_per_hour:
        return False, f"Hourly limit reached ({_hourly_count}/{config.pacing.max_apps_per_hour})"

    # Check time window (apply only during business hours)
    now = datetime.utcnow()  # TODO: convert to config timezone
    hour = now.hour
    if hour < config.pacing.apply_hours_start or hour >= config.pacing.apply_hours_end:
        return False, f"Outside apply hours ({config.pacing.apply_hours_start}-{config.pacing.apply_hours_end})"

    return True, "OK"


def record_application(success: bool, platform: str = ""):
    """Record an application attempt."""
    global _daily_count, _hourly_count
    _daily_count += 1
    _hourly_count += 1

    if not success and platform:
        _platform_failures[platform] += 1


def is_platform_blocked(platform: str) -> bool:
    """Check if a platform has too many failures today (3+ = blocked until tomorrow)."""
    return _platform_failures.get(platform, 0) >= 3


def get_random_delay() -> float:
    """Get randomized delay between applications (18-28 minutes, non-uniform)."""
    r = random.random()
    if r < 0.70:
        # Normal gap (70% of the time)
        return random.uniform(config.pacing.min_gap_seconds, config.pacing.max_gap_seconds)
    elif r < 0.90:
        # Long break (20% of the time)
        return random.uniform(config.pacing.max_gap_seconds, config.pacing.max_gap_seconds * 1.5)
    else:
        # Short gap (10% of the time)
        return random.uniform(config.pacing.min_gap_seconds * 0.7, config.pacing.min_gap_seconds)


def get_backoff_delay(retry_count: int) -> float:
    """Exponential backoff: 30s → 60s → 120s → 240s → 300s max."""
    base = 30
    delay = min(base * (2 ** retry_count), 300)
    # Add jitter
    delay *= random.uniform(0.8, 1.2)
    return delay


def get_stats() -> dict:
    """Get current safety stats."""
    return {
        "daily_count": _daily_count,
        "hourly_count": _hourly_count,
        "daily_limit": config.pacing.max_apps_per_day,
        "hourly_limit": config.pacing.max_apps_per_hour,
        "platform_failures": dict(_platform_failures),
    }
