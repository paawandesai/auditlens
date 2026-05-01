"""Lead capture endpoint — store emails for the PDF download funnel.

POST /api/v1/leads — capture an email before serving a paid/gated artifact.

Used by the frontend modal that prompts for an email before letting the
user download a PDF compliance report.
"""

from __future__ import annotations

import re

from fastapi import HTTPException, Request
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.security.rate_limit import limiter
from app.storage.sqlite_store import get_store

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])

# Minimal RFC-ish email check — we don't need full RFC 5321 here, just enough
# to reject obvious garbage at the boundary. Real validation happens downstream
# (e.g. in the email-sending provider).
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class LeadRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    scan_context: str = Field(default="", max_length=500)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v


@router.post("")
@limiter.limit("20/hour")
async def capture_lead(request: Request, body: LeadRequest) -> dict:
    """Store email for lead generation. SQLite write is best-effort."""
    store = get_store()
    if store is None:
        # Persistence not initialised (e.g. test client without lifespan).
        # Still return success — lead capture must never block the funnel.
        return {"status": "ok"}

    try:
        store.save_lead(email=body.email, scan_context=body.scan_context)
    except Exception:
        # Swallow storage failures; the user is mid-funnel and shouldn't see them.
        # The request will still 200 so the frontend proceeds with the PDF.
        return {"status": "ok"}

    return {"status": "ok"}
