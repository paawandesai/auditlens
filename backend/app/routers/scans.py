"""Scan endpoints — the core API surface.

POST /api/v1/scans/repo — full compliance assessment JSON (public)
POST /api/v1/scans/repo/complete — repo scan + uploaded evidence (public)
POST /api/v1/scans/repo/pdf — audit-ready PDF report (public)
POST /api/v1/scans/repo/export/{platform} — GRC-formatted JSON, demo control IDs (auth required)
GET  /api/v1/scans/export/platforms — available GRC platforms (public)
GET  /api/v1/scans/{scan_id} — retrieve stored scan result (public)
"""

from __future__ import annotations

import time
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.scanners.github_scanner import (
    GitHubScanError,
    GitHubScanner,
    RateLimitError,
    RepoNotFoundError,
)
from app.schemas.compliance import AssessmentResult
from app.schemas.scanner import ScannerOutput
from app.security.auth import AuthUser, require_auth
from app.security.rate_limit import RATE_LIMIT_READ, RATE_LIMIT_SCAN, limiter
from app.services.compliance.article_05 import Article05Check
from app.services.compliance.article_06 import Article06Check
from app.services.compliance.article_08 import Article08Check
from app.services.compliance.article_09 import Article09Check
from app.services.compliance.article_10 import Article10Check
from app.services.compliance.article_11 import Article11Check
from app.services.compliance.article_12 import Article12Check
from app.services.compliance.article_13 import Article13Check
from app.services.compliance.article_14 import Article14Check
from app.services.compliance.article_15 import Article15Check
from app.services.compliance.article_16 import Article16Check
from app.services.compliance.article_17 import Article17Check
from app.services.compliance.article_26 import Article26Check
from app.services.compliance.article_27 import Article27Check
from app.services.compliance.article_50 import Article50Check
from app.services.compliance.article_53 import Article53Check
from app.services.compliance.article_55 import Article55Check
from app.services.compliance.article_72 import Article72Check
from app.services.compliance.base import ComplianceEngine
from app.services.grc.base import AdapterRegistry
from app.services.grc.control_mappings import mapping_disclosure
from app.services.grc.drata_adapter import DrataAdapter
from app.services.grc.generic_adapter import GenericAdapter
from app.services.grc.secureframe_adapter import SecureframeAdapter
from app.services.grc.vanta_adapter import VantaAdapter
from app.services.pdf.report_builder import generate_compliance_pdf
from app.storage.sqlite_store import get_store

router = APIRouter(prefix="/api/v1/scans", tags=["Scanning"])

# Universal checks — apply to ALL AI systems regardless of risk level
UNIVERSAL_CHECKS = [
    Article05Check(),
    Article06Check(),
    Article50Check(),
]

# High-risk technical checks — Art. 9-15
HIGH_RISK_CHECKS = [
    Article08Check(),
    Article09Check(),
    Article10Check(),
    Article11Check(),
    Article12Check(),
    Article13Check(),
    Article14Check(),
    Article15Check(),
]

# Organizational/provider/deployer checks — Art. 16, 17, 26, 27
ORGANIZATIONAL_CHECKS = [
    Article16Check(),
    Article17Check(),
    Article26Check(),
    Article27Check(),
]

# GPAI checks — Art. 53, 55
GPAI_CHECKS = [
    Article53Check(),
    Article55Check(),
]

# Lifecycle checks — Art. 72
LIFECYCLE_CHECKS = [
    Article72Check(),
]

# All checks combined
ALL_CHECKS = (
    UNIVERSAL_CHECKS + HIGH_RISK_CHECKS
    + ORGANIZATIONAL_CHECKS + GPAI_CHECKS + LIFECYCLE_CHECKS
)


# ---------------------------------------------------------------------------
# In-memory scan result store (shareable links)
# ---------------------------------------------------------------------------
_SCAN_STORE: dict[str, dict] = {}
_SCAN_TTL = 86400  # 24 hours


def _store_scan(scan_id: str, data: dict) -> None:
    """Store a scan result with timestamp. Evicts expired entries."""
    now = time.time()
    expired = [k for k, v in _SCAN_STORE.items() if now - v["ts"] > _SCAN_TTL]
    for k in expired:
        del _SCAN_STORE[k]
    _SCAN_STORE[scan_id] = {"data": data, "ts": now}


def _get_scan(scan_id: str) -> dict | None:
    """Retrieve a stored scan result if not expired."""
    entry = _SCAN_STORE.get(scan_id)
    if entry and time.time() - entry["ts"] <= _SCAN_TTL:
        return entry["data"]
    return None


class RepoScanRequest(BaseModel):
    repository_url: str
    branch: str = "main"
    # Role-based scoping — determines which articles are applicable.
    # Valid: "provider", "deployer", "both", "gpai", "gpai_systemic",
    #        "library", "tool", "undeclared". Anything else is normalised
    #        to "undeclared" by the engine.
    role: str = "undeclared"
    # If true, the assessment honours Art. 11(1) simplified-documentation
    # provisions for SMEs (< 250 employees, < EUR 50M turnover).
    sme: bool = False


async def _run_scan(
    request: RepoScanRequest,
) -> tuple[ScannerOutput, AssessmentResult]:
    """Shared scan logic for /repo and /repo/pdf.

    Applies risk-tiered check selection:
    - Art. 5 + 50 always run (universal obligations)
    - Art. 9-15 only scored for HIGH risk; advisory for others
    """
    scanner = GitHubScanner()

    try:
        scanner_output = await scanner.scan(
            repo_url=request.repository_url,
            branch=request.branch,
        )
    except RepoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GitHubScanError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Determine risk tier
    risk_level = "UNDETERMINED"
    if scanner_output.risk_classification:
        risk_level = scanner_output.risk_classification.risk_level

    # All 17 articles assessed for every scan
    # Risk tier determines which are scored vs advisory
    all_article_names = [
        "Article 5", "Article 6", "Article 8", "Article 9", "Article 10",
        "Article 11", "Article 12", "Article 13", "Article 14", "Article 15",
        "Article 16", "Article 17", "Article 26", "Article 27",
        "Article 50", "Article 53", "Article 55", "Article 72",
    ]

    if risk_level == "HIGH":
        # HIGH risk: all articles scored
        scored_checks = ALL_CHECKS
        advisory_checks = None
    else:
        # Non-HIGH: universal + organizational scored; high-risk technical as advisory
        scored_checks = (
            UNIVERSAL_CHECKS + ORGANIZATIONAL_CHECKS
            + GPAI_CHECKS + LIFECYCLE_CHECKS
        )
        advisory_engine = ComplianceEngine(HIGH_RISK_CHECKS)
        advisory_checks = advisory_engine.run_advisory(scanner_output, role=request.role)

    engine = ComplianceEngine(scored_checks)
    assessment = engine.run(scanner_output, role=request.role, sme=request.sme)
    assessment.risk_tier = risk_level
    assessment.applicable_articles = all_article_names
    assessment.advisory_checks = advisory_checks

    return scanner_output, assessment


# ---------------------------------------------------------------------------
# Public endpoints (rate limited, no auth)
# ---------------------------------------------------------------------------


@router.post("/repo")
@limiter.limit(RATE_LIMIT_SCAN)
async def scan_repo(request: Request, body: RepoScanRequest) -> dict:
    """Scan a public GitHub repo and return full compliance assessment."""
    scanner_output, assessment = await _run_scan(body)

    result = {
        "repository": body.repository_url,
        "branch": body.branch,
        "scanner_output": scanner_output.model_dump(),
        "assessment": assessment.model_dump(mode="json"),
    }
    _store_scan(assessment.assessment_id, result)
    store = get_store()
    if store:
        try:
            store.save_scan(assessment.assessment_id, body.repository_url, result)
        except Exception:
            pass  # SQLite failure must not break the request
    return result


class CompleteScanRequest(BaseModel):
    repository_url: str | None = None  # Optional for deployer-only
    branch: str = "main"
    evidence_ids: list[str] = []
    risk_level: str | None = None  # Required if no repo
    role: str = "undeclared"
    sme: bool = False


@router.post("/repo/complete")
@limiter.limit(RATE_LIMIT_SCAN)
async def scan_repo_complete(request: Request, body: CompleteScanRequest) -> dict:
    """Scan repo + merge uploaded evidence for complete compliance assessment.

    Supports three modes:
    1. Repo + evidence: scan GitHub + merge uploaded documents
    2. Repo only: same as /repo (backward compat)
    3. Evidence only (deployer mode): no repo, assess from uploaded docs
    """
    from app.routers.evidence import get_cached_evidence
    from app.services.evidence_merger import (
        EvidenceItem,
        create_empty_scanner_output,
        merge_evidence,
    )

    # Build base scanner output
    if body.repository_url:
        scan_request = RepoScanRequest(
            repository_url=body.repository_url,
            branch=body.branch,
        )
        scanner = GitHubScanner()
        try:
            scanner_output = await scanner.scan(
                repo_url=scan_request.repository_url,
                branch=scan_request.branch,
            )
        except RepoNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RateLimitError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except GitHubScanError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    else:
        # Deployer-only mode — no repo scan
        scanner_output = create_empty_scanner_output()

    # Merge uploaded evidence
    evidence_items = []
    for eid in body.evidence_ids[:10]:  # Cap at 10 documents
        cached = get_cached_evidence(eid)
        if cached:
            evidence_items.append(EvidenceItem(
                evidence_id=eid,
                doc_type=cached["doc_type"],
                filename=cached["filename"],
                description=cached.get("description", ""),
                keyword_matches=cached.get("keyword_analysis", {}).get("matched_keywords", []),
            ))

    if evidence_items:
        scanner_output = merge_evidence(scanner_output, evidence_items)
        # Store evidence metadata in scanner output for PDF/reporting
        scanner_output.external_evidence = [
            {
                "evidence_id": item.evidence_id,
                "doc_type": item.doc_type,
                "filename": item.filename,
                "description": item.description,
                "articles": item.articles,
                "signals": item.signals,
            }
            for item in evidence_items
        ]

    # Auto-infer risk level for deployer mode (no repo to scan)
    if not body.repository_url and not scanner_output.risk_classification:
        from app.services.evidence_merger import DOC_TYPE_ARTICLE_MAP
        from app.schemas.scanner import RiskClassification

        # If any uploaded doc maps to Art. 9-15 articles → HIGH risk
        high_risk_articles = {
            "Article 8", "Article 9", "Article 10", "Article 11",
            "Article 12", "Article 13", "Article 14", "Article 15",
        }
        doc_types = [item.doc_type for item in evidence_items]
        mapped_articles = set()
        for dt in doc_types:
            mapped_articles.update(DOC_TYPE_ARTICLE_MAP.get(dt, []))

        has_high_risk_docs = bool(mapped_articles & high_risk_articles)
        # Most doc types imply HIGH risk; only pure transparency = LIMITED
        inferred_level = "HIGH" if has_high_risk_docs or len(doc_types) > 1 else (
            "LIMITED" if doc_types else "HIGH"  # Default HIGH (safest)
        )

        scanner_output.risk_classification = RiskClassification(
            risk_level=inferred_level,
            risk_score=70 if inferred_level == "HIGH" else 35,
            confidence=0.7,
            evidence=[{
                "signal_type": "evidence_inference",
                "detail": f"Risk level inferred from {len(doc_types)} uploaded document(s): {', '.join(doc_types)}",
                "score": 0.7,
                "weight": 1.0,
            }],
        )

    # Determine risk tier and run compliance engine
    risk_level = "UNDETERMINED"
    if scanner_output.risk_classification:
        risk_level = scanner_output.risk_classification.risk_level

    all_article_names = [
        "Article 5", "Article 6", "Article 8", "Article 9", "Article 10",
        "Article 11", "Article 12", "Article 13", "Article 14", "Article 15",
        "Article 16", "Article 17", "Article 26", "Article 27",
        "Article 50", "Article 53", "Article 55", "Article 72",
    ]

    if risk_level == "HIGH":
        scored_checks = ALL_CHECKS
        advisory_checks = None
    else:
        scored_checks = (
            UNIVERSAL_CHECKS + ORGANIZATIONAL_CHECKS
            + GPAI_CHECKS + LIFECYCLE_CHECKS
        )
        advisory_engine = ComplianceEngine(HIGH_RISK_CHECKS)
        advisory_checks = advisory_engine.run_advisory(scanner_output, role=body.role)

    engine = ComplianceEngine(scored_checks)
    assessment = engine.run(scanner_output, role=body.role, sme=body.sme)
    assessment.risk_tier = risk_level
    assessment.applicable_articles = all_article_names
    assessment.advisory_checks = advisory_checks

    result = {
        "repository": body.repository_url or "deployer://no-repo",
        "branch": body.branch,
        "mode": "complete" if evidence_items else "repo_only",
        "evidence_count": len(evidence_items),
        "scanner_output": scanner_output.model_dump(),
        "assessment": assessment.model_dump(mode="json"),
    }
    _store_scan(assessment.assessment_id, result)
    store = get_store()
    if store:
        try:
            store.save_scan(
                assessment.assessment_id,
                body.repository_url or "deployer://no-repo",
                result,
            )
        except Exception:
            pass  # SQLite failure must not break the request
    return result


@router.get("/export/platforms")
@limiter.limit(RATE_LIMIT_READ)
async def list_export_platforms(request: Request) -> dict:
    """List available GRC export platforms and whether their mappings are demo-only."""
    platforms = GRC_REGISTRY.available_platforms()
    return {
        "platforms": platforms,
        "mapping_status": {p: mapping_disclosure(p)["mapping_status"] for p in platforms},
    }


@router.get("")
@limiter.limit(RATE_LIMIT_READ)
async def list_recent_scans(request: Request, limit: int = 20) -> dict:
    """Return metadata for recently stored scans (newest first)."""
    store = get_store()
    if not store:
        return {"scans": []}
    return {"scans": store.get_recent_scans(limit=min(limit, 100))}


@router.get("/{scan_id}")
@limiter.limit(RATE_LIMIT_READ)
async def get_scan(request: Request, scan_id: str) -> dict:
    """Retrieve a previously stored scan result by ID."""
    result = _get_scan(scan_id)
    if result is None:
        store = get_store()
        if store:
            result = store.get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scan not found or expired")
    return result


@router.post("/repo/pdf")
@limiter.limit(RATE_LIMIT_SCAN)
async def scan_repo_pdf(
    request: Request,
    body: RepoScanRequest,
) -> StreamingResponse:
    """Scan a public GitHub repo and return an audit-ready PDF report.

    Public endpoint — no auth required. PDF download is the lead-gen funnel;
    gate with email capture on the frontend, not backend auth.
    """
    scanner_output, assessment = await _run_scan(body)
    pdf_bytes = generate_compliance_pdf(assessment, scanner_output)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=auditlens-{assessment.assessment_id[:8]}.pdf"
            ),
        },
    )


# ---------------------------------------------------------------------------
# GRC Export (auth required — Enterprise tier)
# ---------------------------------------------------------------------------

GRC_REGISTRY = AdapterRegistry([
    VantaAdapter(),
    DrataAdapter(),
    SecureframeAdapter(),
    GenericAdapter(),
])


@router.post("/repo/export/{platform}")
@limiter.limit(RATE_LIMIT_SCAN)
async def scan_repo_export(
    request: Request,
    platform: str,
    body: RepoScanRequest,
    user: AuthUser = Depends(require_auth),
) -> dict:
    """Scan a repo and return GRC-formatted JSON for the specified platform."""
    adapter = GRC_REGISTRY.get(platform)
    if adapter is None:
        available = GRC_REGISTRY.available_platforms()
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform '{platform}'. Available: {', '.join(available)}",
        )

    _, assessment = await _run_scan(body)
    payload = adapter.translate(assessment)
    payload.update(mapping_disclosure(adapter.platform_name()))
    return payload
