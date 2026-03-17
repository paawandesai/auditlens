"""AuditLens AI — FastAPI Application.

This is the API-first microservice that GRC platforms (Vanta, Drata) consume.
The product IS the JSON output, not a dashboard.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Header, status
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    supabase_url: str = "https://your-project.supabase.co"
    supabase_anon_key: str = "your-anon-key"
    supabase_service_key: str = "your-service-key"
    allowed_origins: list[str] = ["http://localhost:3000"]
    api_key_header: str = "X-AuditLens-Key"
    environment: str = "development"

    class Config:
        env_file = ".env"
        env_prefix = "AUDITLENS_"


settings = Settings()


# ---------------------------------------------------------------------------
# Pydantic Models — Request / Response Schemas
# ---------------------------------------------------------------------------

class ScanStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class ComplianceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class RiskLevel(str, Enum):
    UNACCEPTABLE = "UNACCEPTABLE"
    HIGH = "HIGH"
    LIMITED = "LIMITED"
    MINIMAL = "MINIMAL"
    UNDETERMINED = "UNDETERMINED"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# --- Request Models ---

class ScanRequest(BaseModel):
    """Request to initiate a repository scan."""

    repository_url: HttpUrl = Field(
        ..., description="Git repository URL to scan"
    )
    branch: str = Field(
        default="main", description="Branch to scan"
    )
    scan_depth: str = Field(
        default="standard",
        description="Scan depth: 'quick' (deps only), 'standard' (deps + AST), 'deep' (full analysis)"
    )
    jurisdictions: list[str] = Field(
        default=["EU_AI_ACT"],
        description="Regulatory frameworks to check against"
    )


class FreeScanRequest(BaseModel):
    """Request for the free public scan tool (no auth required)."""

    repository_url: HttpUrl
    email: str | None = Field(
        default=None,
        description="Email to send the full PDF report (gated)"
    )


# --- Response Models ---

class EvidenceItem(BaseModel):
    """Individual evidence signal supporting a classification."""

    signal: str = Field(..., description="Signal type: 'framework', 'purpose', 'data_subject'")
    detail: str = Field(..., description="Human-readable evidence description")
    weight: float = Field(..., ge=0, le=1, description="Signal weight in classification")


class DetectedAISystem(BaseModel):
    """An AI system detected in the scanned repository."""

    system_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    frameworks: list[str]
    purpose: str
    risk_level: RiskLevel
    annex_iii_category: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    evidence: list[EvidenceItem]


class ComplianceCheck(BaseModel):
    """Result of checking a single regulatory article."""

    article: str = Field(..., description="Regulatory article ID, e.g. 'EU_AI_ACT_ART_10'")
    title: str = Field(..., description="Human-readable article title")
    status: ComplianceStatus
    severity: Severity
    evidence: str = Field(..., description="Explanation of the check result")
    remediation: str | None = Field(None, description="Suggested fix if status is FAIL")
    evidence_paths: list[str] = Field(
        default_factory=list,
        description="File paths that were examined"
    )


class ScanResult(BaseModel):
    """Complete scan result — THIS IS THE PRODUCT."""

    scan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository: str
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ScanStatus = ScanStatus.COMPLETE
    ai_systems_detected: list[DetectedAISystem]
    compliance_checks: list[ComplianceCheck]
    overall_status: str = "NON_COMPLIANT"
    risk_score: int = Field(..., ge=0, le=100)
    report_url: str | None = None


class ScanStatusResponse(BaseModel):
    """Status of a running or completed scan."""

    scan_id: str
    status: ScanStatus
    progress_pct: int = 0
    message: str = ""
    result: ScanResult | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str = settings.environment


# ---------------------------------------------------------------------------
# Application Setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AuditLens AI",
    description=(
        "EU AI Act compliance scanning engine. "
        "Detects AI/ML systems in codebases and evaluates regulatory compliance. "
        "Designed as a Black Box API for GRC platform integration (Vanta, Drata, Secureframe)."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

async def verify_api_key(
    x_auditlens_key: str | None = Header(None, alias="X-AuditLens-Key"),
) -> str:
    """Verify the API key for authenticated endpoints."""
    if settings.environment == "development":
        return "dev-key"
    if not x_auditlens_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include 'X-AuditLens-Key' header.",
        )
    # TODO: Validate against Supabase api_keys table
    return x_auditlens_key


# ---------------------------------------------------------------------------
# In-Memory Scan Store (replace with Supabase in production)
# ---------------------------------------------------------------------------

_scan_store: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Background Scan Pipeline
# ---------------------------------------------------------------------------

async def run_scan_pipeline(scan_id: str, request: ScanRequest) -> None:
    """Execute the three-pass scanning pipeline in the background.

    Pass 1: Dependency detection (requirements_parser)
    Pass 2: AST import analysis (TODO)
    Pass 3: Risk classification (risk_classifier)
    Then: Compliance check engine (TODO)
    """
    from app.scanners.requirements_parser import RequirementsParser
    from app.services.risk_classifier import RiskClassifier

    try:
        _scan_store[scan_id]["status"] = ScanStatus.SCANNING
        _scan_store[scan_id]["progress_pct"] = 10

        # --- Pass 1: Dependency Detection ---
        parser = RequirementsParser()
        # In production, this clones the repo and scans actual files.
        # For MVP, we accept a manifest string via a separate endpoint.
        _scan_store[scan_id]["progress_pct"] = 30

        # --- Pass 2: AST Import Analysis (TODO) ---
        _scan_store[scan_id]["progress_pct"] = 50

        # --- Pass 3: Risk Classification ---
        _scan_store[scan_id]["status"] = ScanStatus.ANALYZING
        classifier = RiskClassifier()
        _scan_store[scan_id]["progress_pct"] = 70

        # --- Compliance Checks (TODO) ---
        _scan_store[scan_id]["progress_pct"] = 90

        # --- Finalize ---
        _scan_store[scan_id]["status"] = ScanStatus.COMPLETE
        _scan_store[scan_id]["progress_pct"] = 100

    except Exception as e:
        _scan_store[scan_id]["status"] = ScanStatus.FAILED
        _scan_store[scan_id]["error"] = str(e)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Health check endpoint for load balancers and monitoring."""
    return HealthResponse()


@app.post(
    "/api/v1/scans",
    response_model=ScanStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Scanning"],
)
async def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
) -> ScanStatusResponse:
    """Initiate a new compliance scan on a repository.

    This is the primary endpoint for GRC platform integration.
    Returns immediately with a scan_id; poll /api/v1/scans/{scan_id} for results.
    """
    scan_id = str(uuid.uuid4())
    _scan_store[scan_id] = {
        "status": ScanStatus.PENDING,
        "progress_pct": 0,
        "request": request.model_dump(),
    }

    background_tasks.add_task(run_scan_pipeline, scan_id, request)

    return ScanStatusResponse(
        scan_id=scan_id,
        status=ScanStatus.PENDING,
        progress_pct=0,
        message="Scan queued. Poll this endpoint for status updates.",
    )


@app.get(
    "/api/v1/scans/{scan_id}",
    response_model=ScanStatusResponse,
    tags=["Scanning"],
)
async def get_scan_status(
    scan_id: str,
    api_key: str = Depends(verify_api_key),
) -> ScanStatusResponse:
    """Get the status and results of a scan.

    Poll this endpoint until status is 'complete' or 'failed'.
    When complete, the 'result' field contains the full compliance report.
    """
    if scan_id not in _scan_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found.",
        )

    store = _scan_store[scan_id]
    return ScanStatusResponse(
        scan_id=scan_id,
        status=store["status"],
        progress_pct=store.get("progress_pct", 0),
        message=store.get("error", ""),
        result=store.get("result"),
    )


@app.post(
    "/api/v1/scans/analyze-manifest",
    response_model=ScanResult,
    tags=["Scanning"],
)
async def analyze_manifest(
    manifest_type: str,
    manifest_content: str,
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Quick analysis of a single dependency manifest.

    Useful for testing and for the free scan tool.
    Accepts raw file content and returns classification immediately (synchronous).
    """
    from app.scanners.requirements_parser import RequirementsParser
    from app.services.risk_classifier import RiskClassifier

    parser = RequirementsParser()

    if manifest_type == "requirements.txt":
        detected = parser.parse_requirements_txt(manifest_content)
    elif manifest_type == "package.json":
        detected = parser.parse_package_json(manifest_content)
    elif manifest_type == "pyproject.toml":
        detected = parser.parse_pyproject_toml(manifest_content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported manifest type: {manifest_type}. "
                   f"Supported: requirements.txt, package.json, pyproject.toml",
        )

    classifier = RiskClassifier()
    classifications = classifier.classify_frameworks(detected)

    return {
        "scan_id": str(uuid.uuid4()),
        "repository": "manifest-upload",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "ai_systems_detected": classifications,
        "compliance_checks": [],  # TODO: Implement compliance check engine
        "overall_status": "ASSESSMENT_PENDING",
        "risk_score": 0,
    }


@app.post(
    "/api/v1/free-scan",
    response_model=dict,
    tags=["Free Tool"],
)
async def free_scan(request: FreeScanRequest) -> dict[str, Any]:
    """Free public scan tool — no API key required.

    Returns a summary risk assessment. Full PDF report gated behind email signup.
    This is the distribution hook for programmatic SEO and viral acquisition.
    """
    # TODO: Implement repo cloning and scanning for free tier
    return {
        "repository": str(request.repository_url),
        "summary": {
            "ai_systems_found": 0,
            "risk_level": "UNDETERMINED",
            "message": "Full scan coming soon. Leave your email for early access.",
        },
        "full_report_available": request.email is not None,
    }


# ---------------------------------------------------------------------------
# GRC Integration Endpoints (for Vanta/Drata marketplace)
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/integrations/compliance-payload/{scan_id}",
    tags=["GRC Integration"],
)
async def get_grc_payload(
    scan_id: str,
    format: str = "vanta",
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Get scan results formatted for specific GRC platform integration.

    Formats: 'vanta', 'drata', 'secureframe', 'generic'

    This endpoint transforms our internal scan results into the exact JSON
    schema that each GRC platform expects, making integration frictionless.
    """
    if scan_id not in _scan_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found.",
        )

    # TODO: Implement format-specific transformations
    return {
        "format": format,
        "scan_id": scan_id,
        "payload": {},
        "message": f"GRC payload format '{format}' coming soon.",
    }


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database connections and warm up classifiers."""
    # TODO: Initialize Supabase client
    # TODO: Load framework signatures into memory
    pass


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources."""
    pass
