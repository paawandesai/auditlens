"""Red team ingestion endpoints.

POST /api/v1/redteam/ingest     — ingest findings, return assessment JSON
POST /api/v1/redteam/ingest/pdf — ingest findings, return audit PDF
"""

from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.redteam import RedTeamScanResult
from app.schemas.scanner import ScannerOutput
from app.security.rate_limit import RATE_LIMIT_SCAN, limiter
from app.services.pdf.report_builder import generate_compliance_pdf
from app.services.redteam_mapper import map_redteam_to_assessment
from app.storage.sqlite_store import get_store

router = APIRouter(prefix="/api/v1/redteam", tags=["Red Team"])


@router.post("/ingest")
@limiter.limit(RATE_LIMIT_SCAN)
async def ingest_redteam(request: Request, body: RedTeamScanResult) -> dict:
    """Ingest red team findings and return a compliance assessment."""
    assessment = map_redteam_to_assessment(body)

    result = {
        "scan_id": body.scan_id,
        "assessment": assessment.model_dump(mode="json"),
    }

    store = get_store()
    if store:
        try:
            store.save_redteam_scan(body.scan_id, result)
        except Exception:
            pass

    return result


@router.post("/ingest/pdf")
@limiter.limit(RATE_LIMIT_SCAN)
async def ingest_redteam_pdf(request: Request, body: RedTeamScanResult) -> StreamingResponse:
    """Ingest red team findings and return an audit-ready PDF report."""
    assessment = map_redteam_to_assessment(body)

    target_name = body.target.get("name", body.scan_id)
    scanner_output = ScannerOutput(repo_url=f"Target: {target_name}")

    pdf_bytes = generate_compliance_pdf(assessment, scanner_output)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=redteam_{body.scan_id}.pdf"},
    )
