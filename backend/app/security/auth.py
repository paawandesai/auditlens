"""Authentication — JWT/API key validation for protected routes.

Supports two authentication methods:
1. API Key: `Authorization: Bearer <api_key>` — validated against AUDITLENS_API_KEYS
2. JWT: `Authorization: Bearer <jwt_token>` — validated against AUDITLENS_JWT_SECRET

Configuration via environment variables:
    AUDITLENS_JWT_SECRET     — HMAC secret for JWT signing/verification (required for JWT)
    AUDITLENS_API_KEYS       — comma-separated list of valid API keys
    AUDITLENS_AUTH_ENABLED   — set to "false" to disable auth (dev only, default: true)

Protected routes use `Depends(require_auth)`.
Public routes (scan form, health) have no dependency.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_JWT_SECRET = os.environ.get("AUDITLENS_JWT_SECRET", "")
_JWT_ALGORITHM = "HS256"
_API_KEYS: set[str] = set()
_AUTH_ENABLED = os.environ.get("AUDITLENS_AUTH_ENABLED", "true").lower() != "false"

# Parse comma-separated API keys from env
_raw_keys = os.environ.get("AUDITLENS_API_KEYS", "")
if _raw_keys.strip():
    _API_KEYS = {k.strip() for k in _raw_keys.split(",") if k.strip()}

# Bearer token scheme (auto_error=False so we can provide custom error messages)
_bearer_scheme = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    """Authenticated user context extracted from token."""

    sub: str  # subject (user ID or API key identifier)
    tier: str = "free"  # "free", "pro", "enterprise"
    exp: datetime | None = None


def _validate_jwt(token: str) -> AuthUser:
    """Validate a JWT token and return the authenticated user."""
    if not _JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT authentication not configured (AUDITLENS_JWT_SECRET missing)",
        )
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(
        sub=sub,
        tier=payload.get("tier", "free"),
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC) if "exp" in payload else None,
    )


def _validate_api_key(token: str) -> AuthUser:
    """Validate an API key against the configured allowlist."""
    if token in _API_KEYS:
        return AuthUser(sub=f"apikey:{token[:8]}...", tier="pro")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_auth(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ] = None,
) -> AuthUser:
    """Dependency that enforces authentication on a route.

    Tries JWT first, falls back to API key validation.
    When AUDITLENS_AUTH_ENABLED=false, returns a default user (dev mode).
    """
    if not _AUTH_ENABLED:
        return AuthUser(sub="dev-user", tier="enterprise")

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Try JWT first (JWTs have dots separating header.payload.signature)
    if token.count(".") == 2 and _JWT_SECRET:
        return _validate_jwt(token)

    # Fall back to API key
    if _API_KEYS:
        return _validate_api_key(token)

    # No auth method configured
    if _JWT_SECRET:
        return _validate_jwt(token)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No authentication method configured (set AUDITLENS_JWT_SECRET or AUDITLENS_API_KEYS)",
    )


async def optional_auth(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ] = None,
) -> AuthUser | None:
    """Dependency for routes where auth is optional (e.g., free scan)."""
    if credentials is None:
        return None

    if not _AUTH_ENABLED:
        return AuthUser(sub="dev-user", tier="enterprise")

    token = credentials.credentials

    try:
        if token.count(".") == 2 and _JWT_SECRET:
            return _validate_jwt(token)
        if _API_KEYS:
            return _validate_api_key(token)
    except HTTPException:
        return None

    return None
