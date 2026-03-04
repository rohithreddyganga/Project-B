"""
Jobs routes — scraped jobs list, filtering, details.
Dashboard Section ①: Scraped Jobs List
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.db.models import Job, JobStatus, VisaStatus

router = APIRouter()


@router.get("/")
async def list_jobs(
    status: Optional[str] = None,
    visa: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[float] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List scraped jobs with filters."""
    query = select(Job).order_by(desc(Job.posted_date))

    if status:
        query = query.where(Job.status == status)
    if visa:
        query = query.where(Job.visa_status == visa)
    if source:
        query = query.where(Job.source == source)
    if min_score:
        query = query.where(Job.match_score >= min_score)
    if search:
        query = query.where(
            Job.title.ilike(f"%{search}%") | Job.company.ilike(f"%{search}%")
        )

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "jobs": [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "source": j.source,
                "apply_url": j.apply_url,
                "posted_date": j.posted_date.isoformat() if j.posted_date else None,
                "match_score": j.match_score,
                "visa_status": j.visa_status.value if j.visa_status else None,
                "tier": j.tier.value if j.tier else None,
                "ats_platform": j.ats_platform,
                "status": j.status.value if j.status else None,
                "status_reason": j.status_reason,
                "visa_reason": j.visa_reason,
                "remote": j.remote,
                "salary_min": j.salary_min,
                "salary_max": j.salary_max,
            }
            for j in jobs
        ],
    }


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get full job details including JD text."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return {"error": "Job not found"}, 404

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "source": job.source,
        "apply_url": job.apply_url,
        "jd_text": job.jd_text,
        "posted_date": job.posted_date.isoformat() if job.posted_date else None,
        "match_score": job.match_score,
        "visa_status": job.visa_status.value if job.visa_status else None,
        "tier": job.tier.value if job.tier else None,
        "ats_platform": job.ats_platform,
        "status": job.status.value if job.status else None,
        "status_reason": job.status_reason,
        "visa_reason": job.visa_reason,
        "remote": job.remote,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
    }


@router.get("/stats/sources")
async def job_source_stats(db: AsyncSession = Depends(get_db)):
    """Job count by source."""
    result = await db.execute(
        select(Job.source, func.count(Job.id))
        .group_by(Job.source)
    )
    return {"sources": {row[0]: row[1] for row in result.all()}}
