"""
Match Scorer — orchestrates JD analysis + ATS scoring + tier assignment.
Stage 5-6 of the pipeline.

FIX: The original used min_match_score=80 with use_llm=False.
Without the LLM layer, cosine+keyword scores max out around 40-50%.
The fix: use a LOWER screening threshold for the initial pass (non-LLM),
then let the optimizer bring scores up during the optimization loop.
"""
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.config import config
from src.db.models import Job, JobStatus
from src.scorer.jd_analyzer import analyze_jd
from src.scorer.ats_scorer import score_ats
from src.scorer.tier_classifier import classify_tier


# The initial screening threshold should be MUCH lower than the final target.
# Why? Because use_llm=False means we only use cosine+keywords, which score lower.
# The optimizer will re-score WITH LLM and iterate until hitting 90-96%.
INITIAL_SCREENING_FACTOR = 0.55  # Use 55% of the configured threshold for screening


async def score_and_classify_jobs(
    jobs: List[Job],
    resume_text: str,
    db: AsyncSession,
) -> List[Job]:
    """
    Score each job against the resume and classify tiers.
    Returns jobs that pass the minimum match threshold.
    
    IMPORTANT: The initial screening threshold is intentionally lower than the
    final ATS target. This is a pre-filter, not the final quality gate.
    The optimizer handles the final score optimization.
    """
    configured_min = config.rules.get("min_match_score", 80)
    
    # Use a lower threshold for initial non-LLM screening
    # A job scoring 35% on keywords alone could hit 90%+ after optimization
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

            # Score against resume
            # use_llm=True for better accuracy (costs ~$0.001 per job via Haiku)
            # If you want to save money, set to False — but screening_threshold
            # should be even lower (like 20%) without LLM
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
                    f"✅ PASS: {job.company} — {job.title}: "
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
        f"Scoring complete: {len(passed)} passed (≥{screening_threshold:.0f}%), "
        f"{below} below threshold"
    )

    return passed
