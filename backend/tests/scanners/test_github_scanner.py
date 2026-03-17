"""Tests for GitHubScanner — mocked HTTP via respx."""

from __future__ import annotations

from base64 import b64encode

import httpx
import pytest
import respx

from app.scanners.github_scanner import (
    GitHubScanError,
    GitHubScanner,
    RateLimitError,
    RepoNotFoundError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TREE_RESPONSE = {
    "sha": "abc123",
    "tree": [
        {"path": "README.md", "type": "blob"},
        {"path": "requirements.txt", "type": "blob"},
        {"path": "MODEL_CARD.md", "type": "blob"},
        {"path": "RISK_ASSESSMENT.md", "type": "blob"},
        {"path": "tests", "type": "tree"},
        {"path": "tests/test_model.py", "type": "blob"},
        {"path": ".github/workflows/ci.yml", "type": "blob"},
        {"path": "docs/architecture.md", "type": "blob"},
        {"path": "eval_results.json", "type": "blob"},
        {"path": "bias_report.md", "type": "blob"},
        {"path": "data_card.yaml", "type": "blob"},
    ],
    "truncated": False,
}

README_CONTENT = (
    "# HR AI Model\n\n"
    "Uses SHAP for explainability.\n"
    "Human review is required for all predictions.\n"
    "Override mechanism available.\n"
    "Adversarial testing is performed.\n"
    "Data source: internal HR database.\n"
    "Preprocessing steps documented.\n"
    "Monitoring dashboards track drift.\n"
    "Audit logging is enabled.\n"
)

REQUIREMENTS_CONTENT = "scikit-learn==1.4.0\npandas>=2.0\nfairlearn\n"


def _b64_content(text: str) -> dict:
    return {
        "content": b64encode(text.encode()).decode(),
        "encoding": "base64",
    }


def _rate_limit_headers(remaining: int = 4999) -> dict:
    return {"X-RateLimit-Remaining": str(remaining)}


# ---------------------------------------------------------------------------
# URL Parsing
# ---------------------------------------------------------------------------

class TestParseRepoUrl:

    def setup_method(self):
        self.scanner = GitHubScanner(client=httpx.AsyncClient())

    def test_standard_url(self):
        assert self.scanner.parse_repo_url("https://github.com/owner/repo") == ("owner", "repo")

    def test_url_with_git_suffix(self):
        assert self.scanner.parse_repo_url("https://github.com/owner/repo.git") == ("owner", "repo")

    def test_url_with_trailing_slash(self):
        assert self.scanner.parse_repo_url("https://github.com/owner/repo/") == ("owner", "repo")

    def test_url_with_tree_path(self):
        url = "https://github.com/owner/repo/tree/main"
        assert self.scanner.parse_repo_url(url) == ("owner", "repo")

    def test_url_without_scheme(self):
        assert self.scanner.parse_repo_url("github.com/owner/repo") == ("owner", "repo")

    def test_url_with_whitespace(self):
        assert self.scanner.parse_repo_url("  https://github.com/owner/repo  ") == ("owner", "repo")

    def test_invalid_url_raises(self):
        with pytest.raises(GitHubScanError, match="Invalid GitHub URL"):
            self.scanner.parse_repo_url("https://gitlab.com/owner/repo")

    def test_empty_url_raises(self):
        with pytest.raises(GitHubScanError):
            self.scanner.parse_repo_url("")


# ---------------------------------------------------------------------------
# Tree Fetching
# ---------------------------------------------------------------------------

class TestFetchTree:

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_tree_successfully(self):
        respx.get(
            "https://api.github.com/repos/owner/repo/git/trees/main?recursive=1"
        ).mock(return_value=httpx.Response(200, json=TREE_RESPONSE, headers=_rate_limit_headers()))

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            paths = await scanner._fetch_tree("owner", "repo", "main")

        assert "README.md" in paths
        assert "tests/test_model.py" in paths

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_raises_repo_not_found(self):
        respx.get(
            "https://api.github.com/repos/owner/missing/git/trees/main?recursive=1"
        ).mock(return_value=httpx.Response(
            404, json={"message": "Not Found"}, headers=_rate_limit_headers(),
        ))

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            with pytest.raises(RepoNotFoundError):
                await scanner._fetch_tree("owner", "missing", "main")

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_raises(self):
        respx.get(
            "https://api.github.com/repos/owner/repo/git/trees/main?recursive=1"
        ).mock(return_value=httpx.Response(200, json=TREE_RESPONSE, headers=_rate_limit_headers(0)))

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            with pytest.raises(RateLimitError):
                await scanner._fetch_tree("owner", "repo", "main")


# ---------------------------------------------------------------------------
# Full Scan Pipeline
# ---------------------------------------------------------------------------

class TestScanFullPipeline:

    @respx.mock
    @pytest.mark.asyncio
    async def test_full_scan_compliant_repo(self):
        base = "https://api.github.com"
        headers = _rate_limit_headers()

        # Tree
        respx.get(f"{base}/repos/org/ai-hiring/git/trees/main?recursive=1").mock(
            return_value=httpx.Response(200, json=TREE_RESPONSE, headers=headers)
        )

        # Manifests
        req_url = f"{base}/repos/org/ai-hiring/contents/requirements.txt?ref=main"
        respx.get(req_url).mock(return_value=httpx.Response(
            200, json=_b64_content(REQUIREMENTS_CONTENT), headers=headers,
        ))

        # Content files (README.md, docs/architecture.md, etc.)
        readme_url = f"{base}/repos/org/ai-hiring/contents/README.md?ref=main"
        respx.get(readme_url).mock(return_value=httpx.Response(
            200, json=_b64_content(README_CONTENT), headers=headers,
        ))

        # Doc files discovered from tree
        arch_url = f"{base}/repos/org/ai-hiring/contents/docs/architecture.md?ref=main"
        respx.get(arch_url).mock(return_value=httpx.Response(
            200, json=_b64_content("Architecture docs"), headers=headers,
        ))

        # Mock any other content fetches as 404
        respx.route(method="GET", host="api.github.com").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"}, headers=headers)
        )

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            output = await scanner.scan("https://github.com/org/ai-hiring")

        # Verify file-tree flags
        assert output.has_model_card is True
        assert output.has_risk_assessment is True
        assert output.has_test_suite is True
        assert output.has_versioning is True
        assert output.has_architecture_docs is True
        assert output.has_data_documentation is True

        # Verify content flags
        assert output.has_explainability is True
        assert output.has_human_oversight_docs is True
        assert output.has_override_mechanism is True
        assert output.has_mitigation_plan is True
        assert output.has_logging_config is True

        # Verify inferred flags
        assert output.has_escalation_docs is True  # inferred from human_oversight

        # Verify frameworks detected
        names = {f.name for f in output.detected_frameworks}
        assert "scikit-learn" in names
        assert "fairlearn" in names

        # Verify typed models populated
        assert output.performance_metrics is not None
        assert output.performance_metrics.adversarial_tested is True
        assert output.training_data_stats is not None
        assert output.training_data_stats.provenance_documented is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_scan_empty_repo(self):
        base = "https://api.github.com"
        headers = _rate_limit_headers()

        empty_tree = {"sha": "abc", "tree": [], "truncated": False}
        respx.get(f"{base}/repos/org/empty/git/trees/main?recursive=1").mock(
            return_value=httpx.Response(200, json=empty_tree, headers=headers)
        )

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            output = await scanner.scan("https://github.com/org/empty")

        assert output.has_model_card is False
        assert output.has_test_suite is False
        assert output.detected_frameworks == []
        assert output.performance_metrics is None
        assert output.training_data_stats is None


# ---------------------------------------------------------------------------
# Manifest File Discovery
# ---------------------------------------------------------------------------

class TestFindManifestFiles:

    def setup_method(self):
        self.scanner = GitHubScanner(client=httpx.AsyncClient())

    def test_finds_root_level(self):
        tree = ["README.md", "requirements.txt", "setup.py"]
        result = self.scanner._find_manifest_files(tree, ["requirements.txt", "setup.py"])
        assert "requirements.txt" in result
        assert "setup.py" in result

    def test_finds_nested_manifests(self):
        tree = [
            "README.md",
            "backend/requirements.txt",
            "model/setup.py",
            "frontend/package.json",
        ]
        result = self.scanner._find_manifest_files(
            tree, ["requirements.txt", "setup.py", "package.json"]
        )
        assert "backend/requirements.txt" in result
        assert "model/setup.py" in result
        assert "frontend/package.json" in result

    def test_prefers_root_level(self):
        tree = [
            "requirements.txt",
            "backend/requirements.txt",
            "model/requirements.txt",
        ]
        result = self.scanner._find_manifest_files(tree, ["requirements.txt"])
        assert result[0] == "requirements.txt"  # root first

    def test_caps_at_15(self):
        tree = [f"dir{i}/requirements.txt" for i in range(20)]
        result = self.scanner._find_manifest_files(tree, ["requirements.txt"])
        assert len(result) == 15

    def test_case_insensitive(self):
        tree = ["REQUIREMENTS.TXT", "Setup.py"]
        result = self.scanner._find_manifest_files(
            tree, ["requirements.txt", "setup.py"]
        )
        assert len(result) == 2

    def test_no_matches(self):
        tree = ["README.md", "src/main.py"]
        result = self.scanner._find_manifest_files(tree, ["requirements.txt"])
        assert result == []

    def test_finds_environment_yml(self):
        tree = ["ml/environment.yml", "requirements.txt"]
        result = self.scanner._find_manifest_files(
            tree, ["requirements.txt", "environment.yml"]
        )
        assert "ml/environment.yml" in result


# ---------------------------------------------------------------------------
# Full Scan with Nested Manifests
# ---------------------------------------------------------------------------

class TestScanNestedManifests:

    @respx.mock
    @pytest.mark.asyncio
    async def test_scan_discovers_nested_requirements(self):
        base = "https://api.github.com"
        headers = _rate_limit_headers()

        tree_with_nested = {
            "sha": "abc",
            "tree": [
                {"path": "README.md", "type": "blob"},
                {"path": "backend/requirements.txt", "type": "blob"},
                {"path": "model/setup.py", "type": "blob"},
            ],
            "truncated": False,
        }

        respx.get(f"{base}/repos/org/monorepo/git/trees/main?recursive=1").mock(
            return_value=httpx.Response(200, json=tree_with_nested, headers=headers)
        )

        respx.get(f"{base}/repos/org/monorepo/contents/backend/requirements.txt?ref=main").mock(
            return_value=httpx.Response(
                200, json=_b64_content("torch>=2.0\ntransformers\n"), headers=headers
            )
        )

        setup_py_content = (
            "from setuptools import setup\n"
            "setup(install_requires=['scikit-learn'])\n"
        )
        respx.get(f"{base}/repos/org/monorepo/contents/model/setup.py?ref=main").mock(
            return_value=httpx.Response(
                200, json=_b64_content(setup_py_content), headers=headers
            )
        )

        respx.get(f"{base}/repos/org/monorepo/contents/README.md?ref=main").mock(
            return_value=httpx.Response(
                200, json=_b64_content("# Monorepo\n"), headers=headers
            )
        )

        # Catch-all for other requests
        respx.route(method="GET", host="api.github.com").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"}, headers=headers)
        )

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            output = await scanner.scan("https://github.com/org/monorepo")

        names = {f.name for f in output.detected_frameworks}
        assert "torch" in names
        assert "transformers" in names
        assert "scikit-learn" in names


class TestScanEdgeCases:

    @respx.mock
    @pytest.mark.asyncio
    async def test_repo_not_found(self):
        base = "https://api.github.com/repos/org/missing/git/trees"
        not_found = httpx.Response(
            404, json={"message": "Not Found"}, headers=_rate_limit_headers(),
        )
        respx.get(f"{base}/main?recursive=1").mock(return_value=not_found)
        respx.get(f"{base}/master?recursive=1").mock(return_value=not_found)

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            with pytest.raises(RepoNotFoundError):
                await scanner.scan("https://github.com/org/missing")

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_on_tree(self):
        tree_url = "https://api.github.com/repos/org/repo/git/trees/main?recursive=1"
        respx.get(tree_url).mock(return_value=httpx.Response(
            200, json=TREE_RESPONSE, headers=_rate_limit_headers(0),
        ))

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            with pytest.raises(RateLimitError):
                await scanner.scan("https://github.com/org/repo")

    @respx.mock
    @pytest.mark.asyncio
    async def test_403_raises_rate_limit(self):
        tree_url = "https://api.github.com/repos/org/repo/git/trees/main?recursive=1"
        respx.get(tree_url).mock(return_value=httpx.Response(
            403, json={"message": "Forbidden"}, headers=_rate_limit_headers(0),
        ))

        async with httpx.AsyncClient() as client:
            scanner = GitHubScanner(client=client)
            with pytest.raises(RateLimitError):
                await scanner.scan("https://github.com/org/repo")
