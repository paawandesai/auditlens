"""Evidence upload endpoints — upload compliance documents for analysis.

POST /api/v1/evidence/upload — upload a document, get analysis + evidence_id
GET  /api/v1/evidence/{evidence_id} — retrieve evidence metadata + analysis
GET  /api/v1/evidence/doc-types — list supported document types

Security:
- File type validation (PDF, DOCX, MD, TXT only)
- File size cap (10MB)
- Rate limited (3 uploads/hour per IP)
- LLM calls server-side only (no API key exposure)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form

from app.security.rate_limit import limiter
from app.services.document_analyzer import (
    analyze_keywords,
    analyze_with_llm,
    DOC_TYPE_KEYWORDS,
)
from app.services.evidence_merger import DOC_TYPE_ARTICLE_MAP, DOC_TYPE_SIGNAL_MAP
from app.services.file_processor import (
    FileProcessingError,
    extract_text,
    validate_file,
    MAX_FILE_SIZE,
)
from app.services.storage import EvidenceStorage

router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence"])

# Shared storage instance
_storage = EvidenceStorage()

# In-memory analysis cache (evidence_id → analysis results)
_ANALYSIS_CACHE: dict[str, dict] = {}

MAX_DOCS_PER_SCAN = 10

VALID_DOC_TYPES = list(DOC_TYPE_SIGNAL_MAP.keys())


@router.get("/doc-types")
async def list_doc_types() -> dict:
    """List supported document types and which articles they help satisfy."""
    return {
        "doc_types": [
            {
                "id": doc_type,
                "label": doc_type.replace("_", " ").title(),
                "articles": DOC_TYPE_ARTICLE_MAP.get(doc_type, []),
                "signals": DOC_TYPE_SIGNAL_MAP.get(doc_type, []),
                "keywords_checked": len(DOC_TYPE_KEYWORDS.get(doc_type, [])),
            }
            for doc_type in VALID_DOC_TYPES
        ],
    }


@router.post("/upload")
@limiter.limit("10/hour")
async def upload_evidence(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    description: str = Form(""),
) -> dict:
    """Upload a compliance document for analysis.

    Flow:
    1. Validate file type + size
    2. Extract text from PDF/DOCX/MD/TXT
    3. Run keyword analysis (free, fast)
    4. Run LLM completeness analysis (if enabled)
    5. Store file in Supabase (or in-memory fallback)
    6. Return evidence_id + analysis results

    Args:
        file: The uploaded file (PDF, DOCX, MD, or TXT).
        doc_type: One of: qms, fria, conformity, monitoring_plan,
                  incident_procedure, risk_assessment, data_governance,
                  model_card, human_oversight, transparency.
        description: Optional description of the document.
    """
    # Validate doc_type
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid doc_type '{doc_type}'. Valid types: {', '.join(VALID_DOC_TYPES)}",
        )

    # Read file bytes
    file_bytes = await file.read()

    # Validate file
    try:
        validate_file(
            filename=file.filename or "unknown",
            content_type=file.content_type or "",
            size=len(file_bytes),
        )
    except FileProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Extract text
    try:
        text = extract_text(file_bytes, file.filename or "unknown")
    except FileProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Keyword analysis (always runs)
    keyword_result = analyze_keywords(text, doc_type)

    # LLM analysis (runs if enabled)
    articles = DOC_TYPE_ARTICLE_MAP.get(doc_type, [])
    llm_result = None
    if articles:
        # Use the primary article for LLM analysis
        llm_result = await analyze_with_llm(
            text=text,
            doc_type=doc_type,
            article=articles[0],
            requirements=[],  # Will be populated from taxonomy in production
        )

    # Store file
    stored = await _storage.upload(
        file_bytes=file_bytes,
        filename=file.filename or "unknown",
        doc_type=doc_type,
        description=description,
    )

    # Cache analysis results
    analysis = {
        "evidence_id": stored.evidence_id,
        "filename": stored.filename,
        "doc_type": doc_type,
        "description": description,
        "articles_helped": articles,
        "signals_satisfied": DOC_TYPE_SIGNAL_MAP.get(doc_type, []),
        "keyword_analysis": {
            "coverage_score": keyword_result.coverage_score,
            "matched_keywords": keyword_result.matched_keywords,
            "missing_keywords": keyword_result.missing_keywords[:10],
            "summary": keyword_result.summary,
        },
        "llm_analysis": (
            {
                "completeness_score": llm_result.completeness_score,
                "requirements_satisfied": llm_result.requirements_satisfied,
                "requirements_assessed": llm_result.requirements_assessed,
                "findings": llm_result.findings,
                "summary": llm_result.summary,
            }
            if llm_result
            else None
        ),
        "text_length": len(text),
        "file_size_bytes": stored.size_bytes,
    }
    _ANALYSIS_CACHE[stored.evidence_id] = analysis

    return analysis


@router.get("/{evidence_id}")
async def get_evidence(evidence_id: str) -> dict:
    """Retrieve analysis results for previously uploaded evidence."""
    result = _ANALYSIS_CACHE.get(evidence_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evidence not found or expired")
    return result


def get_cached_evidence(evidence_id: str) -> dict | None:
    """Get cached evidence analysis (used by complete scan endpoint)."""
    return _ANALYSIS_CACHE.get(evidence_id)
