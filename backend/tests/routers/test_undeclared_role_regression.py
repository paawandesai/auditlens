"""Regression: a plain Python library scanned with the default role must not
FAIL deployer-only or GPAI-only obligations.

Repro (PRE_PRODUCT_AUDIT.md, Phase 7 "single biggest risk"): POST a plain
library repo to /api/v1/scans/repo without a `role` field. Before the fix the
engine scored every article for role="undeclared", so the library got a
critical FAIL on Art. 27 (Fundamental Rights Impact Assessment) — an
obligation that only applies to deployers of high-risk systems.
"""

from __future__ import annotations

from base64 import b64encode

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app

BASE = "https://api.github.com"
RATE_HEADERS = {"X-RateLimit-Remaining": "4999"}

LIBRARY_TREE = {
    "sha": "abc",
    "tree": [
        {"path": "README.md", "type": "blob"},
        {"path": "pyproject.toml", "type": "blob"},
        {"path": "src/textutils/__init__.py", "type": "blob"},
        {"path": "src/textutils/slugify.py", "type": "blob"},
        {"path": "tests/test_slugify.py", "type": "blob"},
    ],
    "truncated": False,
}

LIBRARY_FILES = {
    "README.md": "# textutils\n\nSmall string helpers: slugify, truncate, dedent.\n",
    "pyproject.toml": '[project]\nname = "textutils"\ndependencies = ["regex>=2024.1"]\n',
    "src/textutils/__init__.py": "from .slugify import slugify\n",
    "src/textutils/slugify.py": (
        "import re\n\ndef slugify(s):\n    return re.sub(r'\\W+', '-', s).lower()\n"
    ),
}

# Obligations that attach only to deployers (Art. 26, 27) or to providers of
# general-purpose AI models (Art. 53, 55). A codebase cannot evidence either
# role, so with no declared role they must never be scored.
ROLE_DEPENDENT_ARTICLES = {"Article 26", "Article 27", "Article 53", "Article 55"}


def _b64(text: str) -> dict:
    return {"content": b64encode(text.encode()).decode(), "encoding": "base64"}


def _mock_library_repo() -> None:
    respx.get(f"{BASE}/repos/acme/textutils/git/trees/main?recursive=1").mock(
        return_value=httpx.Response(200, json=LIBRARY_TREE, headers=RATE_HEADERS)
    )
    for path, text in LIBRARY_FILES.items():
        respx.get(f"{BASE}/repos/acme/textutils/contents/{path}?ref=main").mock(
            return_value=httpx.Response(200, json=_b64(text), headers=RATE_HEADERS)
        )
    respx.route(method="GET", host="api.github.com").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"}, headers=RATE_HEADERS)
    )


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


@respx.mock
def test_plain_library_default_role_never_fails_fria(api_client: TestClient) -> None:
    _mock_library_repo()

    # No `role` in the body — the default a first-time user gets.
    response = api_client.post(
        "/api/v1/scans/repo",
        json={"repository_url": "https://github.com/acme/textutils"},
    )

    assert response.status_code == 200
    assessment = response.json()["assessment"]
    assert assessment["role"] == "undeclared"

    scored = {c["article"]: c for c in assessment["checks"]}
    advisory = assessment.get("advisory_checks") or []

    # The exact repro: Art. 27 FRIA must not be a FAIL anywhere in the result.
    fria = scored["Article 27"]
    assert fria["status"] != "FAIL"
    assert fria["is_applicable"] is False
    assert "ART_27" not in " ".join(assessment["summary"]["critical_failures"])

    # Same for every other deployer-only / GPAI-only obligation.
    for article in ROLE_DEPENDENT_ARTICLES:
        check = scored[article]
        assert check["status"] == "N/A", f"{article} scored as {check['status']}"
        assert check["is_applicable"] is False
    for check in advisory:
        assert check["article"] not in ROLE_DEPENDENT_ARTICLES or check["status"] != "FAIL"

    # Not-scored articles are excluded from the headline numbers.
    applicable = [c for c in assessment["checks"] if c["is_applicable"]]
    assert assessment["summary"]["total_checks"] == len(applicable)
    assert not ROLE_DEPENDENT_ARTICLES & {c["article"] for c in applicable}


@respx.mock
def test_plain_library_default_role_pdf_builds(api_client: TestClient) -> None:
    _mock_library_repo()

    response = api_client.post(
        "/api/v1/scans/repo/pdf",
        json={"repository_url": "https://github.com/acme/textutils"},
    )

    assert response.status_code == 200
    assert response.content[:4] == b"%PDF"


@respx.mock
def test_declared_deployer_still_scores_fria(api_client: TestClient) -> None:
    """The fix must not hide FRIA from the role it actually applies to."""
    _mock_library_repo()

    response = api_client.post(
        "/api/v1/scans/repo",
        json={"repository_url": "https://github.com/acme/textutils", "role": "deployer"},
    )

    assert response.status_code == 200
    scored = {c["article"]: c for c in response.json()["assessment"]["checks"]}
    assert scored["Article 27"]["is_applicable"] is True
    assert scored["Article 27"]["status"] in {"PASS", "FAIL", "PARTIAL"}
