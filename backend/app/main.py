"""AuditLens AI — API-first EU AI Act compliance scanner."""

from __future__ import annotations

import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.scans import router as scans_router

app = FastAPI(
    title="AuditLens AI",
    version="0.2.0",
    description=(
        "**API-first EU AI Act compliance evidence service.**\n\n"
        "Scans GitHub repositories for AI/ML usage and produces audit-ready "
        "compliance reports formatted for GRC platforms (Vanta, Drata, Secureframe).\n\n"
        "## Capabilities\n"
        "- **9 articles, 38 sub-checks**: Art. 5 (prohibited practices), Art. 9-15 "
        "(high-risk obligations), Art. 50 (transparency)\n"
        "- **Risk-tiered assessment**: Automatic risk classification determines which "
        "articles are scored vs advisory\n"
        "- **AST-based scanning**: Python import detection with file+line precision, "
        "call-chain analysis for 4 regulated patterns\n"
        "- **GRC export**: Vanta, Drata, Secureframe, and generic JSON formats\n"
        "- **PDF reports**: Audit-grade compliance evidence documents\n\n"
        "## Quick Start\n"
        "```bash\n"
        "curl -X POST /api/v1/scans/repo \\\n"
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"repository_url": "https://github.com/org/repo"}\'\n'
        "```"
    ),
    contact={"name": "AuditLens", "url": "https://auditlens.ai"},
)

_default_origins = ["http://localhost:3000", "http://localhost:5173"]
_origins_env = os.environ.get("AUDITLENS_ALLOWED_ORIGINS", "")
try:
    allowed_origins: list[str] = json.loads(_origins_env) if _origins_env.strip() else _default_origins
except (json.JSONDecodeError, TypeError):
    allowed_origins = _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scans_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
