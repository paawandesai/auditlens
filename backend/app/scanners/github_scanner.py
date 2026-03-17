"""GitHub repository scanner — fetches repo data via REST API.

Three-pass scan:
1. File tree — glob-match paths for compliance file patterns
2. Manifests — parse dependency files for ML/AI frameworks
3. Content — keyword-match README and docs for compliance signals

No git clone. Pure HTTP via httpx. Typical scan: 10-20 API calls.
"""

from __future__ import annotations

import asyncio
import os
import re
from base64 import b64decode

import httpx

from app.scanners.content_analyzer import check_file_tree_flags, extract_content_flags
from app.scanners.requirements_parser import RequirementsParser
from app.schemas.scanner import (
    PerformanceMetrics,
    ScannerOutput,
    TrainingDataStats,
)

GITHUB_API = "https://api.github.com"
REQUEST_TIMEOUT = 10.0
MAX_CONCURRENT_FETCHES = 5

# Files to fetch for content analysis (README + common doc files)
CONTENT_FILES: list[str] = [
    "README.md", "readme.md", "README.rst", "README",
    "docs/README.md", ".env.example",
]

# Manifest files to fetch for dependency detection
MANIFEST_FILES: list[str] = [
    "requirements.txt", "pyproject.toml", "package.json",
    "Pipfile", "setup.cfg", "setup.py", "environment.yml",
]


class GitHubScanError(Exception):
    """Base error for GitHub scanning operations."""


class RateLimitError(GitHubScanError):
    """Raised when GitHub API rate limit is exceeded."""


class RepoNotFoundError(GitHubScanError):
    """Raised when the repository does not exist or is inaccessible."""


class GitHubScanner:
    """Scans a public GitHub repo via REST API and produces a ScannerOutput."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT, follow_redirects=True,
        )
        self._parser = RequirementsParser()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

    async def scan(self, repo_url: str, branch: str = "main") -> ScannerOutput:
        """Full 3-pass scan: file tree -> manifests -> content analysis.

        Returns a populated ScannerOutput ready for the ComplianceEngine.
        """
        owner, repo = self.parse_repo_url(repo_url)

        try:
            # Pass 1: Fetch file tree (fallback to master if main not found)
            try:
                file_paths = await self._fetch_tree(owner, repo, branch)
            except RepoNotFoundError:
                if branch == "main":
                    branch = "master"
                    file_paths = await self._fetch_tree(owner, repo, branch)
                else:
                    raise
            tree_flags = check_file_tree_flags(file_paths)

            # Pass 2: Fetch and parse manifests (search at any depth)
            manifest_files = self._find_manifest_files(file_paths, MANIFEST_FILES)
            manifest_contents = await self._fetch_files(owner, repo, branch, manifest_files)
            detected_frameworks = self._parser.parse(manifest_contents)

            # Pass 3: Fetch and analyze content files
            content_files = self._select_existing_files(file_paths, CONTENT_FILES)
            # Also fetch doc files discovered in tree
            doc_files = self._find_doc_files(file_paths)
            all_content_files = list(set(content_files + doc_files))
            file_contents = await self._fetch_files(owner, repo, branch, all_content_files)
            content_flags = extract_content_flags(file_contents)

            return self._build_output(
                repo_url=repo_url,
                detected_frameworks=detected_frameworks,
                tree_flags=tree_flags,
                content_flags=content_flags,
            )
        finally:
            if not self._external_client:
                await self._client.aclose()

    def parse_repo_url(self, url: str) -> tuple[str, str]:
        """Extract (owner, repo) from a GitHub URL.

        Supports:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - https://github.com/owner/repo/
        - https://github.com/owner/repo/tree/main
        - github.com/owner/repo
        """
        url = url.strip().rstrip("/")

        # Remove .git suffix
        if url.endswith(".git"):
            url = url[:-4]

        # Try regex match
        match = re.match(
            r"(?:https?://)?github\.com/([^/]+)/([^/]+)(?:/.*)?$", url
        )
        if not match:
            raise GitHubScanError(f"Invalid GitHub URL: {url}")

        owner, repo = match.group(1), match.group(2)
        if not owner or not repo:
            raise GitHubScanError(f"Invalid GitHub URL: {url}")

        return owner, repo

    async def _fetch_tree(self, owner: str, repo: str, branch: str) -> list[str]:
        """Fetch the full file tree via the Git Trees API."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        response = await self._api_get(url)

        tree = response.get("tree", [])
        return [item["path"] for item in tree if item.get("type") in ("blob", "tree")]

    async def _fetch_files(
        self, owner: str, repo: str, branch: str, paths: list[str]
    ) -> dict[str, str]:
        """Fetch multiple files concurrently, returning {filename: content}."""
        results: dict[str, str] = {}

        async def fetch_one(path: str) -> tuple[str, str | None]:
            async with self._semaphore:
                url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}"
                try:
                    data = await self._api_get(url)
                    content = data.get("content", "")
                    encoding = data.get("encoding", "")
                    if encoding == "base64" and content:
                        return path, b64decode(content).decode("utf-8", errors="replace")
                    return path, content
                except (GitHubScanError, httpx.HTTPError):
                    return path, None

        tasks = [fetch_one(p) for p in paths]
        completed = await asyncio.gather(*tasks)

        for path, content in completed:
            if content is not None:
                results[path] = content

        return results

    async def _api_get(self, url: str) -> dict:
        """Make a GET request to GitHub API with rate limit checking."""
        headers = {"Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = await self._client.get(url, headers=headers)

        # Check rate limit
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) <= 0:
            raise RateLimitError("GitHub API rate limit exceeded")

        if response.status_code == 404:
            raise RepoNotFoundError(f"Repository not found: {url}")
        if response.status_code == 403:
            raise RateLimitError("GitHub API access forbidden (rate limit or permissions)")

        response.raise_for_status()
        return response.json()

    def _find_manifest_files(
        self, tree_paths: list[str], target_names: list[str]
    ) -> list[str]:
        """Find manifest files at any depth, preferring root-level.

        Unlike _select_existing_files which does exact path matching,
        this matches by filename regardless of directory depth.
        """
        target_set = {t.lower() for t in target_names}
        matches = [
            p for p in tree_paths
            if p.rsplit("/", 1)[-1].lower() in target_set
        ]
        # Sort: root-level first, then by depth
        matches.sort(key=lambda p: p.count("/"))
        return matches[:15]  # Cap to avoid excessive API calls

    def _select_existing_files(
        self, tree_paths: list[str], target_files: list[str]
    ) -> list[str]:
        """Return target files that actually exist in the repo tree."""
        tree_set = {p.lower() for p in tree_paths}
        return [f for f in target_files if f.lower() in tree_set]

    def _find_doc_files(self, file_paths: list[str]) -> list[str]:
        """Find documentation files worth fetching for content analysis."""
        doc_patterns = [
            r"^docs/.*\.md$",
            r"^docs/.*\.rst$",
            r"^.*model.card.*$",
            r"^.*risk.assessment.*$",
        ]
        results: list[str] = []
        for path in file_paths:
            lower = path.lower()
            if any(re.match(pat, lower) for pat in doc_patterns):
                results.append(path)
        # Limit to avoid excessive fetches
        return results[:10]

    def _build_output(
        self,
        repo_url: str,
        detected_frameworks: list,
        tree_flags: dict[str, bool],
        content_flags: dict[str, bool | dict[str, bool]],
    ) -> ScannerOutput:
        """Merge all scan results into a ScannerOutput."""
        # Merge boolean flags — tree OR content match triggers True
        merged: dict[str, bool] = {}
        bool_fields = [
            "has_model_card", "has_risk_assessment", "has_data_documentation",
            "has_explainability", "has_human_oversight_docs", "has_logging_config",
            "has_versioning", "has_test_suite", "has_architecture_docs",
            "has_feature_importance_docs", "has_override_mechanism",
            "has_failure_modes_doc", "has_mitigation_plan",
        ]
        for field in bool_fields:
            merged[field] = bool(tree_flags.get(field)) or bool(content_flags.get(field))

        # Inferred flags
        merged["has_escalation_docs"] = merged.get("has_human_oversight_docs", False)

        # User instructions contribute to model_card signal
        if tree_flags.get("user_instructions_found"):
            merged["has_model_card"] = True

        # Build TrainingDataStats if any sub-signals present
        training_sub = content_flags.get("training_data_sub", {})
        if isinstance(training_sub, dict):
            provenance = bool(training_sub.get("provenance_documented"))
            preprocessing = bool(training_sub.get("preprocessing_documented"))
        else:
            provenance = False
            preprocessing = False

        has_bias = bool(tree_flags.get("bias_analysis_found"))
        has_data_doc = merged.get("has_data_documentation", False)

        training_data_stats = None
        if provenance or preprocessing or has_bias or has_data_doc:
            training_data_stats = TrainingDataStats(
                provenance_documented=provenance,
                preprocessing_documented=preprocessing,
                class_balance={"default": {"class_a": 50, "class_b": 50}} if has_bias else None,
                quality_metrics_logged=has_data_doc,
            )

        # Build PerformanceMetrics if metrics files found
        has_metrics = bool(tree_flags.get("performance_metrics_present"))
        adversarial = bool(content_flags.get("adversarial_tested"))

        performance_metrics = None
        if has_metrics or adversarial:
            performance_metrics = PerformanceMetrics(
                adversarial_tested=adversarial,
            )

        return ScannerOutput(
            repo_url=repo_url,
            detected_frameworks=detected_frameworks,
            **{k: v for k, v in merged.items()},
            training_data_stats=training_data_stats,
            performance_metrics=performance_metrics,
        )
