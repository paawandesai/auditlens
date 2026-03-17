"""Scan endpoints — the core API surface.

POST /api/v1/scans/repo — full compliance assessment JSON
POST /api/v1/scans/repo/pdf — audit-ready PDF report
POST /api/v1/scans/repo/export/{platform} — GRC-formatted JSON
GET  /api/v1/scans/export/platforms — available GRC platforms
"""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, HTTPException
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
from app.services.compliance.article_09 import Article09Check
from app.services.compliance.article_10 import Article10Check
from app.services.compliance.article_11 import Article11Check
from app.services.compliance.article_12 import Article12Check
from app.services.compliance.article_13 import Article13Check
from app.services.compliance.article_14 import Article14Check
from app.services.compliance.article_15 import Article15Check
from app.services.compliance.base import ComplianceEngine
from app.services.grc.base import AdapterRegistry
from app.services.grc.drata_adapter import DrataAdapter
from app.services.grc.generic_adapter import GenericAdapter
from app.services.grc.secureframe_adapter import SecureframeAdapter
from app.services.grc.vanta_adapter import VantaAdapter
from app.services.pdf.report_builder import generate_compliance_pdf

router = APIRouter(prefix="/api/v1/scans", tags=["Scanning"])

ALL_CHECKS = [
    Article09Check(),
    Article10Check(),
    Article11Check(),
    Article12Check(),
    Article13Check(),
    Article14Check(),
    Article15Check(),
]


class RepoScanRequest(BaseModel):
    repository_url: str
    branch: str = "main"


async def _run_scan(
    request: RepoScanRequest,
) -> tuple[ScannerOutput, AssessmentResult]:
    """Shared scan logic for /repo and /repo/pdf."""
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

    engine = ComplianceEngine(ALL_CHECKS)
    assessment = engine.run(scanner_output)
    return scanner_output, assessment


@router.post("/repo")
async def scan_repo(request: RepoScanRequest) -> dict:
    """Scan a public GitHub repo and return full compliance assessment."""
    scanner_output, assessment = await _run_scan(request)

    return {
        "repository": request.repository_url,
        "branch": request.branch,
        "scanner_output": scanner_output.model_dump(),
        "assessment": assessment.model_dump(mode="json"),
    }


@router.post("/repo/pdf")
async def scan_repo_pdf(request: RepoScanRequest) -> StreamingResponse:
    """Scan a public GitHub repo and return an audit-ready PDF report."""
    scanner_output, assessment = await _run_scan(request)
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
# GRC Export
# ---------------------------------------------------------------------------

GRC_REGISTRY = AdapterRegistry([
    VantaAdapter(),
    DrataAdapter(),
    SecureframeAdapter(),
    GenericAdapter(),
])


@router.get("/export/platforms")
async def list_export_platforms() -> dict:
    """List available GRC export platforms."""
    return {"platforms": GRC_REGISTRY.available_platforms()}


@router.post("/repo/export/{platform}")
async def scan_repo_export(platform: str, request: RepoScanRequest) -> dict:
    """Scan a repo and return GRC-formatted JSON for the specified platform."""
    adapter = GRC_REGISTRY.get(platform)
    if adapter is None:
        available = GRC_REGISTRY.available_platforms()
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform '{platform}'. Available: {', '.join(available)}",
        )

    _, assessment = await _run_scan(request)
    return adapter.translate(assessment)
