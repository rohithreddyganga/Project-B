"""
Daily Report Generator + Telegram Notifications.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from src.db.database import get_async_session
from src.db.models import Application, ApplicationStatus, DailyStats
from src.llm_client import get_cost_buffer

logger = logging.getLogger(__name__)


async def generate_daily_report() -> dict:
    """Generate daily stats summary."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    async with get_async_session() as session:
        # Count by status for today
        statuses = {}
        for status in ApplicationStatus:
            result = await session.execute(
                select(func.count(Application.id)).where(
                    and_(
                        Application.scraped_at >= today,
                        Application.scraped_at < tomorrow,
                        Application.status == status,
                    )
                )
            )
            count = result.scalar() or 0
            if count > 0:
                statuses[status.value] = count

        # Submitted today
        result = await session.execute(
            select(func.count(Application.id)).where(
                and_(
                    Application.applied_at >= today,
                    Application.applied_at < tomorrow,
                    Application.status == ApplicationStatus.SUBMITTED,
                )
            )
        )
        submitted_today = result.scalar() or 0

        # Avg ATS score of submitted
        result = await session.execute(
            select(func.avg(Application.ats_score)).where(
                and_(
                    Application.applied_at >= today,
                    Application.applied_at < tomorrow,
                    Application.status == ApplicationStatus.SUBMITTED,
                )
            )
        )
        avg_ats = result.scalar() or 0

        # Total ever submitted
        result = await session.execute(
            select(func.count(Application.id)).where(
                Application.status == ApplicationStatus.SUBMITTED,
            )
        )
        total_submitted = result.scalar() or 0

        # Cost tracking
        cost_buf = get_cost_buffer()
        total_cost = sum(c.get("cost_usd", 0) for c in cost_buf)

    report = {
        "date": today.strftime("%Y-%m-%d"),
        "statuses": statuses,
        "submitted_today": submitted_today,
        "total_submitted": total_submitted,
        "avg_ats_score": round(avg_ats, 1),
        "total_cost_today": round(total_cost, 4),
    }

    logger.info(f"Daily report: {report}")
    return report


def format_telegram_report(report: dict) -> str:
    """Format report as Telegram message."""
    lines = [
        f"📊 *AutoApply Daily Report — {report['date']}*",
        "",
        f"✅ Submitted today: *{report['submitted_today']}*",
        f"📈 Total submitted: *{report['total_submitted']}*",
        f"🎯 Avg ATS score: *{report['avg_ats_score']}%*",
        f"💰 Cost today: *${report['total_cost_today']:.2f}*",
        "",
        "📋 Status breakdown:",
    ]
    for status, count in report.get("statuses", {}).items():
        lines.append(f"  • {status}: {count}")

    return "\n".join(lines)
