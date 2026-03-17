"""AuditLens AI — API-first EU AI Act compliance scanner."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.scans import router as scans_router

app = FastAPI(
    title="AuditLens AI",
    version="0.1.0",
    description="Scan GitHub repositories for AI/ML compliance against EU AI Act.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scans_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
