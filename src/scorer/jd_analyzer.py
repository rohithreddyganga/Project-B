"""
JD Analyzer — extracts structured requirements from job descriptions.
Uses Claude Haiku for intelligent extraction.
"""
import json
import re
from typing import Dict, List, Optional

import anthropic
from loguru import logger
from src.config import config


class JDAnalysis:
    """Structured JD analysis result."""
    def __init__(self, data: dict):
        self.required_skills: List[str] = data.get("required_skills", [])
        self.preferred_skills: List[str] = data.get("preferred_skills", [])
        self.title_keywords: List[str] = data.get("title_keywords", [])
        self.experience_years: Optional[int] = data.get("experience_years")
        self.education_required: Optional[str] = data.get("education_required")
        self.key_responsibilities: List[str] = data.get("key_responsibilities", [])
        self.tools_and_technologies: List[str] = data.get("tools_and_technologies", [])
        self.action_verbs: List[str] = data.get("action_verbs", [])
        self.industry_terms: List[str] = data.get("industry_terms", [])

    @property
    def all_keywords(self) -> List[str]:
        """All extracted keywords combined."""
        return list(set(
            self.required_skills +
            self.preferred_skills +
            self.title_keywords +
            self.tools_and_technologies +
            self.industry_terms
        ))


async def analyze_jd(jd_text: str) -> JDAnalysis:
    """
    Extract structured requirements from a JD using Claude Haiku.
    Falls back to regex extraction if API is unavailable.
    """
    api_key = config.env.anthropic_api_key
    if not api_key or not jd_text:
        return _regex_fallback(jd_text or "")

    prompt = """Extract structured requirements from this job description.
Return a JSON object with these fields:
{
  "required_skills": ["Python", "Java", ...],
  "preferred_skills": ["Kubernetes", ...],
  "title_keywords": ["Software Engineer", "Backend Developer", ...],
  "experience_years": 3,
  "education_required": "Bachelor's in CS or equivalent",
  "key_responsibilities": ["Design microservices", ...],
  "tools_and_technologies": ["AWS", "Docker", "PostgreSQL", ...],
  "action_verbs": ["design", "implement", "optimize", ...],
  "industry_terms": ["microservices", "CI/CD", "agile", ...]
}

Be thorough — extract EVERY technical term, tool, framework, and skill mentioned.
Return ONLY valid JSON, no other text.

Job Description:
"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=config.llm_config.get("scoring_model", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt + jd_text[:4000]}],
        )

        text = response.content[0].text.strip()
        # Clean potential markdown wrapping
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        data = json.loads(text)
        return JDAnalysis(data)

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"JD analysis LLM failed, using regex fallback: {e}")
        return _regex_fallback(jd_text)


def _regex_fallback(jd_text: str) -> JDAnalysis:
    """Simple regex-based keyword extraction as fallback."""
    text = jd_text.lower()

    # Common tech keywords to look for
    tech_patterns = [
        "python", "java", "javascript", "typescript", "c\\+\\+", "c#", "go", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r\\b",
        "react", "angular", "vue", "node\\.js", "express", "django", "flask",
        "spring boot", "spring", "fastapi", ".net",
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
        "terraform", "jenkins", "ci/cd", "github actions",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "kafka", "rabbitmq", "graphql", "rest api", "grpc",
        "machine learning", "deep learning", "nlp", "computer vision",
        "tensorflow", "pytorch", "langchain", "llm",
        "microservices", "distributed systems", "system design",
        "agile", "scrum", "jira", "git",
        "sql", "nosql", "data pipeline", "etl", "spark", "hadoop",
    ]

    found = []
    for pat in tech_patterns:
        if re.search(r'\b' + pat + r'\b', text):
            found.append(pat.replace("\\b", "").replace("\\.", ".").replace("\\+", "+"))

    # Extract years of experience
    years_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s+)?experience', text)
    years = int(years_match.group(1)) if years_match else None

    return JDAnalysis({
        "required_skills": found,
        "preferred_skills": [],
        "title_keywords": [],
        "experience_years": years,
        "tools_and_technologies": found,
        "action_verbs": [],
        "industry_terms": [],
    })
