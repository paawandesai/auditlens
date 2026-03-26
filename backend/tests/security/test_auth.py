"""Tests for authentication — JWT and API key validation."""

from __future__ import annotations

import time

import jwt
import pytest

from app.security.auth import AuthUser, _validate_api_key, _validate_jwt


class TestJwtValidation:
    """Tests for JWT token validation."""

    SECRET = "test-secret-key-for-unit-tests"

    def _make_token(self, payload: dict, secret: str | None = None) -> str:
        return jwt.encode(payload, secret or self.SECRET, algorithm="HS256")

    def test_valid_token(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._JWT_SECRET", self.SECRET)
        token = self._make_token({
            "sub": "user-123",
            "tier": "pro",
            "exp": int(time.time()) + 3600,
        })
        user = _validate_jwt(token)
        assert user.sub == "user-123"
        assert user.tier == "pro"

    def test_expired_token_raises_401(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._JWT_SECRET", self.SECRET)
        token = self._make_token({
            "sub": "user-123",
            "exp": int(time.time()) - 3600,
        })
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_jwt(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_invalid_token_raises_401(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._JWT_SECRET", self.SECRET)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_jwt("not.a.jwt")
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises_401(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._JWT_SECRET", self.SECRET)
        token = self._make_token(
            {"sub": "user-123", "exp": int(time.time()) + 3600},
            secret="wrong-secret",
        )
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_jwt(token)
        assert exc_info.value.status_code == 401

    def test_missing_sub_raises_401(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._JWT_SECRET", self.SECRET)
        token = self._make_token({"exp": int(time.time()) + 3600})
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_jwt(token)
        assert exc_info.value.status_code == 401
        assert "sub" in exc_info.value.detail.lower()

    def test_no_secret_configured_raises_500(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._JWT_SECRET", "")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_jwt("any.token.here")
        assert exc_info.value.status_code == 500

    def test_default_tier_is_free(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._JWT_SECRET", self.SECRET)
        token = self._make_token({
            "sub": "user-456",
            "exp": int(time.time()) + 3600,
        })
        user = _validate_jwt(token)
        assert user.tier == "free"


class TestApiKeyValidation:
    """Tests for API key validation."""

    def test_valid_api_key(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._API_KEYS", {"key-abc-123", "key-def-456"})
        user = _validate_api_key("key-abc-123")
        assert user.sub.startswith("apikey:")
        assert user.tier == "pro"

    def test_invalid_api_key_raises_401(self, monkeypatch):
        monkeypatch.setattr("app.security.auth._API_KEYS", {"key-abc-123"})
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_api_key("wrong-key")
        assert exc_info.value.status_code == 401


class TestAuthUserModel:
    """Tests for AuthUser Pydantic model."""

    def test_default_tier(self):
        user = AuthUser(sub="test")
        assert user.tier == "free"
        assert user.exp is None

    def test_custom_tier(self):
        user = AuthUser(sub="test", tier="enterprise")
        assert user.tier == "enterprise"
