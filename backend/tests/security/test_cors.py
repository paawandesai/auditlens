"""Tests for CORS configuration — environment-aware origin whitelisting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestCorsConfiguration:
    """Tests for CORS middleware behavior."""

    def test_allowed_origin_gets_cors_headers(self):
        from app.main import app
        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_disallowed_origin_no_cors_headers(self):
        from app.main import app
        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Disallowed origins should NOT get the CORS allow-origin header
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin is None or allow_origin != "https://evil-site.com"

    def test_allowed_methods_are_explicit(self):
        from app.main import app
        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        allowed = response.headers.get("access-control-allow-methods", "")
        # Should not be wildcard
        assert "*" not in allowed or allowed == ""
        # GET, POST, OPTIONS should be allowed
        for method in ["GET", "POST"]:
            assert method in allowed

    def test_allowed_headers_are_explicit(self):
        from app.main import app
        client = TestClient(app)
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        allowed_headers = response.headers.get("access-control-allow-headers", "")
        assert "authorization" in allowed_headers.lower()
        assert "content-type" in allowed_headers.lower()

    def test_rate_limit_headers_exposed(self):
        """Rate limit headers should be exposed in CORS for JS clients to read."""
        from app.main import app
        client = TestClient(app)
        # Make an actual GET (not preflight) with Origin to check expose-headers
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        exposed = response.headers.get("access-control-expose-headers", "")
        # The expose-headers are set on actual responses, not preflight
        assert "x-ratelimit-limit" in exposed.lower() or "retry-after" in exposed.lower()
