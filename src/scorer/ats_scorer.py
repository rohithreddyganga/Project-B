"""
3-Layer ATS Scorer.
Layer 1: TF-IDF cosine similarity (semantic match)
Layer 2: Exact keyword hit-rate (critical terms)
Layer 3: Claude Haiku validation (nuanced gaps)
"""
import re
from typing import Optional

import anthropic
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger

from src.config import config
from src.scorer.jd_analyzer import JDAnalysis


async def score_ats(
    resume_text: str,
    jd_text: str,
    jd_analysis: JDAnalysis,
    use_llm: bool = True,
) -> float:
    """
    Compute ATS compatibility score (0-100) using 3-layer approach.
    Weights from config: keyword 0.45, cosine 0.30, llm 0.25.
    """
    weights = config.scoring_config
    kw_weight = weights.get("keyword_weight", 0.45)
    cos_weight = weights.get("cosine_weight", 0.30)
    llm_weight = weights.get("llm_weight", 0.25)

    # Layer 1: TF-IDF Cosine Similarity
    cosine_score = _compute_cosine(resume_text, jd_text)

    # Layer 2: Exact Keyword Hit-Rate
    keyword_score = _compute_keyword_hits(resume_text, jd_analysis)

    # Layer 3: LLM Validation (optional — skip for speed in bulk scoring)
    if use_llm:
        llm_score = await _llm_score(resume_text, jd_text)
    else:
        llm_score = (cosine_score + keyword_score) / 2  # Estimate if no LLM
        llm_weight = 0.0
        # Redistribute weight
        total = kw_weight + cos_weight
        kw_weight = kw_weight / total if total > 0 else 0.5
        cos_weight = cos_weight / total if total > 0 else 0.5

    # Weighted combination
    final = (cosine_score * cos_weight) + (keyword_score * kw_weight) + (llm_score * llm_weight)

    logger.debug(
        f"ATS Score: {final:.1f}% "
        f"(cosine={cosine_score:.1f}, keywords={keyword_score:.1f}, llm={llm_score:.1f})"
    )
    return round(final, 1)


def _compute_cosine(resume_text: str, jd_text: str) -> float:
    """Layer 1: TF-IDF cosine similarity for semantic match."""
    if not resume_text or not jd_text:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2),  # Unigrams and bigrams
        )
        tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return min(score * 100, 100.0)
    except Exception as e:
        logger.warning(f"Cosine similarity error: {e}")
        return 0.0


def _compute_keyword_hits(resume_text: str, jd_analysis: JDAnalysis) -> float:
    """Layer 2: Exact keyword hit-rate for critical terms."""
    all_keywords = jd_analysis.all_keywords
    if not all_keywords:
        return 50.0  # Neutral if no keywords extracted

    resume_lower = resume_text.lower()
    hits = 0
    total = len(all_keywords)

    for keyword in all_keywords:
        kw_lower = keyword.lower().strip()
        if not kw_lower:
            total -= 1
            continue

        # Check for exact match or close variation
        # "CI/CD" should match "ci/cd" or "ci cd"
        variations = [kw_lower, kw_lower.replace("/", " "), kw_lower.replace("-", " ")]
        if any(v in resume_lower for v in variations):
            hits += 1
        # Also check for partial matches (e.g., "javascript" matches "JavaScript/TypeScript")
        elif any(word in resume_lower for word in kw_lower.split() if len(word) > 2):
            hits += 0.5

    if total <= 0:
        return 50.0

    score = (hits / total) * 100
    return min(score, 100.0)


async def _llm_score(resume_text: str, jd_text: str) -> float:
    """Layer 3: Claude Haiku rates the resume-JD match."""
    api_key = config.env.anthropic_api_key
    if not api_key:
        return 50.0

    prompt = f"""Rate how well this resume matches this job description on a 0-100 scale.
Consider: keyword match, skills alignment, experience level, and overall fit.
Respond with ONLY a number between 0 and 100.

RESUME (first 2000 chars):
{resume_text[:2000]}

JOB DESCRIPTION (first 2000 chars):
{jd_text[:2000]}

Score (0-100):"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=config.llm_config.get("scoring_model", "claude-haiku-4-5-20251001"),
            max_tokens=16,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Extract number
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            score = float(match.group(1))
            return min(max(score, 0), 100)

    except Exception as e:
        logger.warning(f"LLM scoring failed: {e}")

    return 50.0  # Neutral fallback
