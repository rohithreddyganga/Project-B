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


# Without LLM, cosine+keyword scores max out around 40-50%.
# Use 55% of the configured threshold for initial non-LLM screening.
INITIAL_SCREENING_FACTOR = 0.55


async def score_and_classify_jobs(
    jobs: List[Job],
    resume_text: str,
    db: AsyncSession,
) -> List[Job]:
    """
    Score each job against the resume and classify tiers.
    Returns jobs that pass the minimum match threshold.

    The initial screening threshold is intentionally lower than the final ATS
    target. This is a pre-filter; the optimizer handles final score optimization.
    """
    configured_min = config.rules.get("min_match_score", 80)

    # Use a lower threshold for initial non-LLM screening
    screening_threshold = max(configured_min * INITIAL_SCREENING_FACTOR, 25)

    logger.info(
        f"Scoring {len(jobs)} jobs "
        f"(screening threshold: {screening_threshold:.0f}%, "
        f"final target: {configured_min}%)"
    )

    passed: List[Job] = []
    below = 0

    for job in jobs:
        try:
            job.status = JobStatus.scoring

            # Analyze JD
            jd_analysis = await analyze_jd(job.jd_text or "")

            # Use LLM if API key is available, otherwise keyword-only
            use_llm = bool(config.env.anthropic_api_key)

            score = await score_ats(
                resume_text=resume_text,
                jd_text=job.jd_text or "",
                jd_analysis=jd_analysis,
                use_llm=use_llm,
            )
            job.match_score = score

            if score >= screening_threshold:
                # Classify tier
                job.tier = classify_tier(job)
                job.status = JobStatus.queued
                passed.append(job)
                logger.info(
                    f"PASS: {job.company} — {job.title}: "
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
    logger.info(
        f"Scoring complete: {len(passed)} passed (>={screening_threshold:.0f}%), "
        f"{below} below threshold"
    )

    return passed
