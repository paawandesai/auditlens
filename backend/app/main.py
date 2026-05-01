"""AuditLens AI — API-first EU AI Act compliance scanner."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routers.evidence import router as evidence_router
from app.routers.leads import router as leads_router
from app.routers.redteam import router as redteam_router
from app.routers.scans import router as scans_router
from app.routers.taxonomy import router as taxonomy_router
from app.security.rate_limit import limiter
from app.storage.sqlite_store import init_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_store()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="AuditLens AI",
    version="0.3.0",
    description=(
        "**API-first EU AI Act compliance evidence service.**\n\n"
        "Scans GitHub repositories and adversarial red team results for AI/ML usage "
        "and produces audit-ready compliance reports formatted for GRC platforms "
        "(Vanta, Drata, Secureframe).\n\n"
        "## Capabilities\n"
        "- **18 articles, 83 sub-checks**: Art. 5 (prohibited practices), "
        "Art. 6 & 8 (classification), Art. 9–15 (high-risk technical obligations), "
        "Art. 16–17 (provider obligations), Art. 26–27 (deployer obligations), "
        "Art. 50 (transparency), Art. 53 & 55 (general-purpose AI), "
        "Art. 72 (post-market monitoring)\n"
        "- **Risk-tiered assessment**: Automatic risk classification determines which "
        "articles are scored vs advisory\n"
        "- **AST-based scanning**: Python import detection with file+line precision, "
        "call-chain analysis for 4 regulated patterns\n"
        "- **Red team ingestion**: Adversarial findings mapped directly to "
        "Articles 9, 12, 14, 15\n"
        "- **GRC export**: Vanta, Drata, Secureframe, and generic JSON formats\n"
        "- **PDF reports**: Audit-grade compliance evidence documents\n\n"
        "## Authentication\n"
        "GRC export endpoints require a Bearer token. Repo scanning, PDF downloads, "
        "evidence upload, and red team ingestion are public.\n\n"
        "## Rate Limits\n"
        "Scan endpoints: 10 requests/minute per IP.\n"
        "Read endpoints: 60 requests/minute per IP.\n\n"
        "## Quick Start\n"
        "```bash\n"
        "curl -X POST /api/v1/scans/repo \\\n"
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"repository_url": "https://github.com/org/repo"}\'\n'
        "```"
    ),
    contact={"name": "AuditLens", "url": "https://auditlens.ai"},
)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — environment-aware, restrictive by default
# ---------------------------------------------------------------------------
_ENV = os.environ.get("AUDITLENS_ENV", "development")

# Default origins: localhost only for development
_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Production origins from env (JSON array)
_origins_env = os.environ.get("AUDITLENS_ALLOWED_ORIGINS", "")
try:
    _configured_origins: list[str] = json.loads(_origins_env) if _origins_env.strip() else []
except (json.JSONDecodeError, TypeError):
    _configured_origins = []

# In production, ONLY use configured origins. In dev, allow localhost.
if _ENV == "production" and _configured_origins:
    allowed_origins = _configured_origins
elif _configured_origins:
    allowed_origins = _configured_origins + _DEV_ORIGINS
else:
    allowed_origins = _DEV_ORIGINS

# Explicit method and header allowlists (not wildcards)
_ALLOWED_METHODS = ["GET", "POST", "OPTIONS"]
_ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "X-Request-ID",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=_ALLOWED_METHODS,
    allow_headers=_ALLOWED_HEADERS,
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"],
    max_age=600,  # Cache preflight for 10 minutes
)

app.include_router(scans_router)
app.include_router(evidence_router)
app.include_router(taxonomy_router)
app.include_router(redteam_router)
app.include_router(leads_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
