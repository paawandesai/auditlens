"""Scan endpoints — the core API surface.

POST /api/v1/scans/repo accepts a GitHub URL and returns a full
compliance assessment against EU AI Act Articles 9-15.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scanners.github_scanner import (
    GitHubScanError,
    GitHubScanner,
    RateLimitError,
    RepoNotFoundError,
)
from app.services.compliance.article_09 import Article09Check
from app.services.compliance.article_10 import Article10Check
from app.services.compliance.article_11 import Article11Check
from app.services.compliance.article_12 import Article12Check
from app.services.compliance.article_13 import Article13Check
from app.services.compliance.article_14 import Article14Check
from app.services.compliance.article_15 import Article15Check
from app.services.compliance.base import ComplianceEngine

router = APIRouter(prefix="/api/v1/scans", tags=["Scanning"])

ALL_CHECKS = [
    Article09Check(),
    Article10Check(),
    Article11Check(),
    Article12Check(),
    Article13Check(),
    Article14Check(),
    Article15Check(),
]


class RepoScanRequest(BaseModel):
    repository_url: str
    branch: str = "main"


@router.post("/repo")
async def scan_repo(request: RepoScanRequest) -> dict:
    """Scan a public GitHub repo and return full compliance assessment."""
    scanner = GitHubScanner()

    try:
        scanner_output = await scanner.scan(
            repo_url=request.repository_url,
            branch=request.branch,
        )
    except RepoNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except GitHubScanError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    engine = ComplianceEngine(ALL_CHECKS)
    assessment = engine.run(scanner_output)

    return {
        "repository": request.repository_url,
        "branch": request.branch,
        "scanner_output": scanner_output.model_dump(),
        "assessment": assessment.model_dump(mode="json"),
    }
