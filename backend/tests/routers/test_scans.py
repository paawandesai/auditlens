"""Tests for scan router — end-to-end API tests."""

from __future__ import annotations

from base64 import b64encode

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


TREE_RESPONSE = {
    "sha": "abc",
    "tree": [
        {"path": "README.md", "type": "blob"},
        {"path": "requirements.txt", "type": "blob"},
        {"path": "tests/test_model.py", "type": "blob"},
    ],
    "truncated": False,
}

RATE_HEADERS = {"X-RateLimit-Remaining": "4999"}


def _b64(text: str) -> dict:
    return {"content": b64encode(text.encode()).decode(), "encoding": "base64"}


class TestHealthEndpoint:

    def test_health(self, api_client):
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestScanRepoEndpoint:

    @respx.mock
    def test_successful_scan(self, api_client):
        base = "https://api.github.com"

        respx.get(f"{base}/repos/org/repo/git/trees/main?recursive=1").mock(
            return_value=httpx.Response(200, json=TREE_RESPONSE, headers=RATE_HEADERS)
        )
        respx.get(f"{base}/repos/org/repo/contents/requirements.txt?ref=main").mock(
            return_value=httpx.Response(200, json=_b64("scikit-learn==1.4\n"), headers=RATE_HEADERS)
        )
        respx.get(f"{base}/repos/org/repo/contents/README.md?ref=main").mock(
            return_value=httpx.Response(200, json=_b64("# My ML Project\n"), headers=RATE_HEADERS)
        )
        # Catch any other requests
        respx.route(method="GET", host="api.github.com").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"}, headers=RATE_HEADERS)
        )

        response = api_client.post(
            "/api/v1/scans/repo",
            json={"repository_url": "https://github.com/org/repo"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["repository"] == "https://github.com/org/repo"
        assert "assessment" in data
        assert "scanner_output" in data
        assert data["assessment"]["summary"]["total_checks"] == 7

    @respx.mock
    def test_repo_not_found_returns_404(self, api_client):
        base = "https://api.github.com/repos/org/missing/git/trees"
        not_found = httpx.Response(
            404, json={"message": "Not Found"}, headers=RATE_HEADERS,
        )
        respx.get(f"{base}/main?recursive=1").mock(return_value=not_found)
        respx.get(f"{base}/master?recursive=1").mock(return_value=not_found)

        response = api_client.post(
            "/api/v1/scans/repo",
            json={"repository_url": "https://github.com/org/missing"},
        )
        assert response.status_code == 404

    @respx.mock
    def test_rate_limit_returns_429(self, api_client):
        respx.get(
            "https://api.github.com/repos/org/repo/git/trees/main?recursive=1"
        ).mock(return_value=httpx.Response(
            200, json=TREE_RESPONSE, headers={"X-RateLimit-Remaining": "0"}
        ))

        response = api_client.post(
            "/api/v1/scans/repo",
            json={"repository_url": "https://github.com/org/repo"},
        )
        assert response.status_code == 429

    def test_invalid_request_body(self, api_client):
        response = api_client.post(
            "/api/v1/scans/repo",
            json={"bad_field": "value"},
        )
        assert response.status_code == 422

    @respx.mock
    def test_custom_branch(self, api_client):
        base = "https://api.github.com"
        empty_tree = {"sha": "abc", "tree": [], "truncated": False}

        respx.get(f"{base}/repos/org/repo/git/trees/develop?recursive=1").mock(
            return_value=httpx.Response(200, json=empty_tree, headers=RATE_HEADERS)
        )

        response = api_client.post(
            "/api/v1/scans/repo",
            json={"repository_url": "https://github.com/org/repo", "branch": "develop"},
        )
        assert response.status_code == 200
