"""Taxonomy endpoints — compliance framework maps and jurisdiction coverage.

GET /api/v1/taxonomy/eu-ai-act — full EU AI Act article taxonomy
GET /api/v1/taxonomy/jurisdictions — all supported and coming-soon jurisdictions
GET /api/v1/taxonomy/summary — high-level coverage statistics
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.security.rate_limit import RATE_LIMIT_READ, limiter
from app.services.taxonomy.eu_ai_act import EU_AI_ACT_TAXONOMY, get_taxonomy_summary
from app.services.taxonomy.jurisdictions import JURISDICTIONS, get_jurisdictions_summary

router = APIRouter(prefix="/api/v1/taxonomy", tags=["Taxonomy"])


@router.get("/eu-ai-act")
@limiter.limit(RATE_LIMIT_READ)
async def get_eu_ai_act_taxonomy(request: Request) -> dict:
    """Return complete EU AI Act article taxonomy with coverage status.

    Maps all company-facing articles, showing which are automated (scanner),
    which require questionnaire, and which need document upload.
    """
    return {
        "framework": "EU AI Act",
        "framework_id": "eu_ai_act",
        "version": "Regulation (EU) 2024/1689",
        "summary": get_taxonomy_summary(),
        "articles": [a.model_dump() for a in EU_AI_ACT_TAXONOMY],
    }


@router.get("/jurisdictions")
@limiter.limit(RATE_LIMIT_READ)
async def get_jurisdictions(request: Request) -> dict:
    """Return all supported and coming-soon AI compliance jurisdictions.

    Each jurisdiction includes its law details, enforcement status,
    requirement overlaps with our scanner signals, and coverage percentage.
    """
    return {
        "summary": get_jurisdictions_summary(),
        "jurisdictions": [j.model_dump() for j in JURISDICTIONS],
    }


@router.get("/summary")
@limiter.limit(RATE_LIMIT_READ)
async def get_taxonomy_overview(request: Request) -> dict:
    """High-level overview of all compliance frameworks and coverage."""
    eu_summary = get_taxonomy_summary()
    jur_summary = get_jurisdictions_summary()

    return {
        "eu_ai_act": {
            "articles_covered": eu_summary["coverage"]["full"],
            "articles_total": eu_summary["total_articles"],
            "requirements_automated": eu_summary["coverage"]["requirements_covered"],
            "requirements_total": eu_summary["coverage"]["requirements_total"],
            "coverage_pct": eu_summary["coverage"]["percentage"],
        },
        "jurisdictions": {
            "supported": jur_summary["supported"],
            "coming_soon": jur_summary["coming_soon"],
            "total": jur_summary["total_jurisdictions"],
            "active_laws": jur_summary["active_laws"],
        },
        "scanner_signals_used": 45,
        "compliance_frameworks": [
            {"id": j.law_id, "name": j.short_name, "status": j.coverage_status}
            for j in JURISDICTIONS
        ],
    }
