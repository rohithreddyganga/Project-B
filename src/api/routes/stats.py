"""
Stats routes — cost tracking, analytics.
Dashboard Section ⑦: Costs & Rules Panel
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.db.models import Application, Job, CostLog, JobStatus, InterviewStage

router = APIRouter()


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Dashboard overview statistics."""
    # Total applications
    total_apps = (await db.execute(
        select(func.count(Application.id))
    )).scalar() or 0

    # Today's applications
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_apps = (await db.execute(
        select(func.count(Application.id))
        .where(Application.applied_date >= today)
        .where(Application.status == JobStatus.submitted.value)
    )).scalar() or 0

    # Success rate
    submitted = (await db.execute(
        select(func.count(Application.id))
        .where(Application.status == JobStatus.submitted.value)
    )).scalar() or 0
    failed = (await db.execute(
        select(func.count(Application.id))
        .where(Application.status == JobStatus.failed.value)
    )).scalar() or 0
    success_rate = submitted / max(submitted + failed, 1) * 100

    # Interviews
    interview_stages = [
        InterviewStage.phone_screen.value,
        InterviewStage.technical.value,
        InterviewStage.final_round.value,
        InterviewStage.offer.value,
    ]
    interviews = (await db.execute(
        select(func.count(Application.id))
        .where(Application.interview_stage.in_(interview_stages))
    )).scalar() or 0

    # Jobs scraped today
    scraped_today = (await db.execute(
        select(func.count(Job.id))
        .where(Job.created_at >= today)
    )).scalar() or 0

    # Average ATS score
    avg_ats = (await db.execute(
        select(func.avg(Application.ats_score))
        .where(Application.ats_score.isnot(None))
    )).scalar() or 0

    return {
        "total_applications": total_apps,
        "today_applications": today_apps,
        "success_rate": round(success_rate, 1),
        "total_interviews": interviews,
        "scraped_today": scraped_today,
        "avg_ats_score": round(float(avg_ats), 1),
    }


@router.get("/costs")
async def get_costs(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Cost breakdown over the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # By category
    result = await db.execute(
        select(CostLog.category, func.sum(CostLog.amount_usd))
        .where(CostLog.created_at >= since)
        .group_by(CostLog.category)
    )
    by_category = {row[0]: round(row[1], 2) for row in result.all()}

    # Total
    total = sum(by_category.values())

    # Daily breakdown
    result = await db.execute(
        select(
            func.date(CostLog.created_at),
            func.sum(CostLog.amount_usd),
        )
        .where(CostLog.created_at >= since)
        .group_by(func.date(CostLog.created_at))
        .order_by(func.date(CostLog.created_at))
    )
    daily = [{"date": str(row[0]), "cost": round(row[1], 2)} for row in result.all()]

    # Per-application cost
    app_count = (await db.execute(
        select(func.count(Application.id))
        .where(Application.applied_date >= since)
    )).scalar() or 1

    return {
        "total_cost": round(total, 2),
        "by_category": by_category,
        "daily": daily,
        "per_application": round(total / app_count, 3),
        "period_days": days,
    }


@router.get("/daily")
async def get_daily_stats(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
):
    """Daily application count for charts."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Application.applied_date),
            func.count(Application.id),
        )
        .where(Application.applied_date >= since)
        .where(Application.status == JobStatus.submitted.value)
        .group_by(func.date(Application.applied_date))
        .order_by(func.date(Application.applied_date))
    )

    return {
        "daily": [
            {"date": str(row[0]), "count": row[1]}
            for row in result.all()
        ]
    }
