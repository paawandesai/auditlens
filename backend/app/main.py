"""AuditLens AI — API-first EU AI Act compliance scanner."""

from __future__ import annotations

import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.scans import router as scans_router

app = FastAPI(
    title="AuditLens AI",
    version="0.1.0",
    description="Scan GitHub repositories for AI/ML compliance against EU AI Act.",
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
