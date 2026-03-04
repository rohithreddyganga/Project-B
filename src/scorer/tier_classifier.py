"""
Tier Classifier — assigns Standard or Top-Tier to each job.
Top-Tier jobs get 96%+ ATS target, 3 iterations, and cover letters.
"""
from src.config import config
from src.db.models import Job, Tier, VisaStatus
from loguru import logger


def classify_tier(job: Job) -> Tier:
    """
    Classify a job as standard or top_tier based on multiple signals.
    Top-tier signals:
      - Company is on priority list
      - JD explicitly mentions visa sponsorship
      - Match score >= 90%
      - Salary in top bracket
      - Exact title match with target titles
    """
    top_tier_signals = 0

    # Signal 1: Priority company
    if config.is_priority_company(job.company):
        top_tier_signals += 2  # Strong signal
        logger.debug(f"Tier: {job.company} is a priority company (+2)")

    # Signal 2: Visa sponsorship explicitly mentioned
    if job.visa_status == VisaStatus.ok:
        jd_lower = (job.jd_text or "").lower()
        sponsor_signals = ["visa sponsorship", "will sponsor", "sponsorship available",
                          "opt welcome", "open to sponsorship"]
        if any(sig in jd_lower for sig in sponsor_signals):
            top_tier_signals += 1
            logger.debug(f"Tier: {job.company} explicitly sponsors (+1)")

    # Signal 3: High match score
    if job.match_score and job.match_score >= 90:
        top_tier_signals += 1
        logger.debug(f"Tier: {job.company} match score {job.match_score}% (+1)")

    # Signal 4: Good salary
    if job.salary_min and job.salary_min >= 120000:
        top_tier_signals += 1

    # Signal 5: Exact title match
    target_titles = [t.lower() for t in config.job_criteria.get("titles", [])]
    if any(t == job.title.lower().strip() for t in target_titles):
        top_tier_signals += 1

    # Threshold: 2+ signals = top tier
    tier = Tier.top_tier if top_tier_signals >= 2 else Tier.standard
    logger.debug(
        f"Tier classification: {job.company} — {job.title} → "
        f"{tier.value} (signals={top_tier_signals})"
    )
    return tier
