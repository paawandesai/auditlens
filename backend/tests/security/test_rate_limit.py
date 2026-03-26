"""Tests for rate limiting configuration and behavior."""

from __future__ import annotations

from app.security.rate_limit import (
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_READ,
    RATE_LIMIT_SCAN,
    _get_client_ip,
    limiter,
)


class TestRateLimitConfig:
    """Tests for rate limit configuration."""

    def test_default_scan_limit(self):
        assert RATE_LIMIT_SCAN == "10/minute"

    def test_default_read_limit(self):
        assert RATE_LIMIT_READ == "60/minute"

    def test_default_global_limit(self):
        assert RATE_LIMIT_DEFAULT == "100/minute"

    def test_limiter_exists(self):
        assert limiter is not None


class TestClientIpExtraction:
    """Tests for IP extraction from requests."""

    def test_forwarded_for_header(self):
        """Should extract first IP from X-Forwarded-For chain."""

        class FakeRequest:
            headers = {"X-Forwarded-For": "1.2.3.4, 10.0.0.1, 172.16.0.1"}
            client = type("C", (), {"host": "127.0.0.1"})()
            scope = {"type": "http"}

        ip = _get_client_ip(FakeRequest())
        assert ip == "1.2.3.4"

    def test_direct_connection(self):
        """Should fall back to direct client IP."""

        class FakeRequest:
            headers = {}
            client = type("C", (), {"host": "192.168.1.100"})()
            scope = {"type": "http"}

        ip = _get_client_ip(FakeRequest())
        assert ip == "192.168.1.100"
