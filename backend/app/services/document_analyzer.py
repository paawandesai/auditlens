"""Document analyzer — keyword + LLM analysis for uploaded compliance docs.

Two-tier analysis:
1. Keyword analysis (always runs, free) — checks for article-specific terms
2. LLM completeness scoring (optional, capped) — Claude Haiku assesses gaps

Security:
- ANTHROPIC_API_KEY stored server-side only (Render env vars)
- API key never exposed in responses or logs
- LLM calls gated by AUDITLENS_LLM_ENABLED env var
- Text input truncated to MAX_TEXT_LENGTH before LLM call
- LLM timeout: 30 seconds
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_TEXT_LENGTH = 100_000  # ~50 pages
LLM_TIMEOUT = 30
LLM_MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Keyword rules per document type
# ---------------------------------------------------------------------------

# Each doc_type maps to keywords that SHOULD appear in a compliant document.
# These are specific to the article requirements the doc_type serves.

DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "qms": [
        "quality management", "quality policy", "quality objective",
        "design control", "document control", "change management",
        "corrective action", "preventive action", "management review",
        "internal audit", "risk management", "incident reporting",
        "training", "competence",
    ],
    "fria": [
        "fundamental rights", "impact assessment", "affected persons",
        "data protection", "non-discrimination", "equality",
        "human dignity", "proportionality", "oversight",
        "complaint mechanism", "redress",
    ],
    "conformity": [
        "conformity assessment", "declaration of conformity", "notified body",
        "technical documentation", "ce marking", "harmonised standard",
        "self-assessment", "third-party assessment", "test report",
    ],
    "monitoring_plan": [
        "monitoring", "post-market", "performance tracking",
        "drift detection", "incident", "alert", "threshold",
        "data collection", "analysis", "feedback", "update",
    ],
    "incident_procedure": [
        "incident", "serious incident", "reporting", "notification",
        "root cause", "corrective action", "escalation", "timeline",
        "authority notification", "documentation",
    ],
    "risk_assessment": [
        "risk identification", "risk analysis", "risk evaluation",
        "risk treatment", "mitigation", "residual risk", "risk matrix",
        "likelihood", "severity", "impact", "foreseeable misuse",
        "failure mode", "testing",
    ],
    "data_governance": [
        "data governance", "data quality", "provenance", "lineage",
        "bias", "fairness", "representativeness", "preprocessing",
        "annotation", "labeling", "data protection", "consent",
    ],
    "model_card": [
        "model card", "intended use", "limitation", "performance",
        "accuracy", "training data", "evaluation", "architecture",
        "version", "contact", "ethical consideration",
    ],
    "human_oversight": [
        "human oversight", "human-in-the-loop", "override", "escalation",
        "stop", "halt", "intervention", "review", "approval",
        "automation bias", "decision support",
    ],
    "transparency": [
        "transparency", "disclosure", "informed", "explanation",
        "explainability", "interpretability", "user instruction",
        "provider", "contact", "version", "capability", "limitation",
    ],
}


@dataclass
class KeywordAnalysisResult:
    """Result of keyword-based document analysis."""

    doc_type: str
    total_keywords: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    coverage_score: float  # 0.0 - 1.0
    summary: str


@dataclass
class LlmAnalysisResult:
    """Result of LLM-based document completeness analysis."""

    doc_type: str
    article: str
    requirements_assessed: int
    requirements_satisfied: int
    completeness_score: float  # 0.0 - 1.0
    findings: list[dict]  # {requirement_id, satisfied, evidence_quote, gap}
    summary: str


@dataclass
class DocumentAnalysis:
    """Combined analysis result for an uploaded document."""

    keyword_result: KeywordAnalysisResult
    llm_result: LlmAnalysisResult | None = None
    signals_satisfied: list[str] = field(default_factory=list)


def analyze_keywords(text: str, doc_type: str) -> KeywordAnalysisResult:
    """Fast keyword extraction against article-specific requirement lists.

    Always runs. Free. Deterministic.
    """
    keywords = DOC_TYPE_KEYWORDS.get(doc_type, [])
    if not keywords:
        return KeywordAnalysisResult(
            doc_type=doc_type,
            total_keywords=0,
            matched_keywords=[],
            missing_keywords=[],
            coverage_score=0.0,
            summary=f"No keyword rules defined for doc_type '{doc_type}'.",
        )

    lower_text = text.lower()
    matched = [kw for kw in keywords if kw in lower_text]
    missing = [kw for kw in keywords if kw not in lower_text]
    score = len(matched) / len(keywords) if keywords else 0.0

    summary = (
        f"Keyword analysis: {len(matched)}/{len(keywords)} expected terms found "
        f"({score:.0%} coverage). "
    )
    if missing and score < 1.0:
        summary += f"Missing: {', '.join(missing[:5])}"
        if len(missing) > 5:
            summary += f" (+{len(missing) - 5} more)"

    return KeywordAnalysisResult(
        doc_type=doc_type,
        total_keywords=len(keywords),
        matched_keywords=matched,
        missing_keywords=missing,
        coverage_score=score,
        summary=summary,
    )


async def analyze_with_llm(
    text: str,
    doc_type: str,
    article: str,
    requirements: list[dict],
) -> LlmAnalysisResult | None:
    """Claude Haiku assesses document completeness against article requirements.

    Only runs if AUDITLENS_LLM_ENABLED=true and ANTHROPIC_API_KEY is set.
    Returns None if LLM is disabled or unavailable.

    Args:
        text: Extracted document text (pre-truncated).
        doc_type: Document type (e.g., "qms", "fria").
        article: EU AI Act article (e.g., "Article 17").
        requirements: List of requirement dicts from taxonomy.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    llm_enabled = os.environ.get("AUDITLENS_LLM_ENABLED", "true").lower() == "true"

    if not llm_enabled or not api_key:
        return None

    # Truncate text for LLM input
    truncated = text[:MAX_TEXT_LENGTH]

    # Build requirement list for prompt
    req_text = "\n".join(
        f"- {r.get('requirement_id', 'N/A')}: {r.get('description', '')}"
        for r in requirements
    )

    prompt = f"""You are an EU AI Act compliance analyst. Assess this {doc_type} document against {article} requirements.

For each requirement listed below, determine if the document provides sufficient evidence. Respond ONLY with valid JSON — no other text.

Format:
{{
  "findings": [
    {{
      "requirement_id": "ART17_1a",
      "satisfied": true,
      "evidence_quote": "exact quote from document (max 200 chars)",
      "gap": "what's missing if not satisfied (empty string if satisfied)"
    }}
  ],
  "summary": "1-2 sentence overall assessment"
}}

Requirements for {article}:
{req_text}

Document text:
{truncated[:50000]}"""

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=LLM_MODEL,
            max_tokens=2000,
            timeout=LLM_TIMEOUT,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse JSON response
        response_text = response.content[0].text
        result = json.loads(response_text)
        findings = result.get("findings", [])
        satisfied = sum(1 for f in findings if f.get("satisfied"))

        return LlmAnalysisResult(
            doc_type=doc_type,
            article=article,
            requirements_assessed=len(findings),
            requirements_satisfied=satisfied,
            completeness_score=satisfied / len(findings) if findings else 0.0,
            findings=findings,
            summary=result.get("summary", "LLM analysis complete."),
        )

    except json.JSONDecodeError:
        return LlmAnalysisResult(
            doc_type=doc_type,
            article=article,
            requirements_assessed=0,
            requirements_satisfied=0,
            completeness_score=0.0,
            findings=[],
            summary="LLM response could not be parsed. Falling back to keyword analysis.",
        )
    except Exception:
        # Any LLM failure is non-fatal — keyword analysis still provides value
        return None
