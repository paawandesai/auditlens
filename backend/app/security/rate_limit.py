"""Rate limiting — IP-based request throttling for all public endpoints.

Uses slowapi (wrapping the `limits` library) with in-memory storage.
Configurable via environment variables:

    RATE_LIMIT_SCAN   — requests/minute for scan endpoints (default: 10/minute)
    RATE_LIMIT_READ   — requests/minute for read endpoints (default: 60/minute)
    RATE_LIMIT_DEFAULT — fallback rate (default: 100/minute)

Returns HTTP 429 with standard rate-limit headers:
    X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
"""

from __future__ import annotations

import os

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

RATE_LIMIT_SCAN = os.environ.get("RATE_LIMIT_SCAN", "10/minute")
RATE_LIMIT_READ = os.environ.get("RATE_LIMIT_READ", "60/minute")
RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "100/minute")


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the chain is the original client
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Single limiter instance — attach to the FastAPI app in main.py
limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=[RATE_LIMIT_DEFAULT],
    storage_uri="memory://",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom 429 handler with standard rate-limit headers."""
    # Extract limit info from the exception
    retry_after = getattr(exc, "retry_after", 60)

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please slow down.",
            "retry_after": retry_after,
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(exc.detail) if hasattr(exc, "detail") else RATE_LIMIT_DEFAULT,
        },
    )
