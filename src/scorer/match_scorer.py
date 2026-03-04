"""
Match Scorer — orchestrates JD analysis + ATS scoring + tier assignment.
Stage 5-6 of the pipeline.
"""
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.config import config
from src.db.models import Job, JobStatus
from src.scorer.jd_analyzer import analyze_jd
from src.scorer.ats_scorer import score_ats
from src.scorer.tier_classifier import classify_tier


async def score_and_classify_jobs(
    jobs: List[Job],
    resume_text: str,
    db: AsyncSession,
) -> List[Job]:
    """
    Score each job against the resume and classify tiers.
    Returns jobs that pass the minimum match threshold.
    """
    min_score = config.rules.get("min_match_score", 80)
    passed: List[Job] = []
    below = 0

    for job in jobs:
        try:
            job.status = JobStatus.scoring

            # Analyze JD
            jd_analysis = await analyze_jd(job.jd_text or "")

            # Score against resume (skip LLM for initial bulk scoring)
            score = await score_ats(
                resume_text=resume_text,
                jd_text=job.jd_text or "",
                jd_analysis=jd_analysis,
                use_llm=False,  # Fast pass — LLM used during optimization
            )
            job.match_score = score

            if score >= min_score:
                # Classify tier
                job.tier = classify_tier(job)
                job.status = JobStatus.queued
                passed.append(job)
                logger.debug(
                    f"Score: {job.company} — {job.title}: "
                    f"{score:.1f}% ({job.tier.value})"
                )
            else:
                job.status = JobStatus.below_threshold
                below += 1

        except Exception as e:
            logger.error(f"Scoring error for {job.company} — {job.title}: {e}")
            job.status = JobStatus.below_threshold
            below += 1

    await db.commit()
    logger.info(f"Scoring: {len(passed)} passed (≥{min_score}%), {below} below threshold")

    return passed
