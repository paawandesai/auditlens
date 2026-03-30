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

from app.scanners.config_scanner import scan_docker_compose, scan_env_content, scan_terraform
from app.scanners.content_analyzer import (
    check_file_tree_flags,
    extract_content_flags,
    validate_doc_sections,
)
from app.scanners.domain_detector import detect_domains
from app.scanners.call_chain_analyzer import analyze_call_chains
from app.scanners.import_scanner import (
    merge_frameworks,
    scan_python_imports_ast,
    select_python_files,
)
from app.scanners.js_import_scanner import (
    scan_js_imports,
    select_js_files,
)
from app.scanners.notebook_scanner import extract_notebook_cells, select_notebook_files
from app.scanners.requirements_parser import RequirementsParser
from app.schemas.scanner import (
    CallChainFinding,
    ConfigSignal,
    DetectedDomain,
    DetectedFramework,
    DetectedImport,
    DocValidation,
    PerformanceMetrics,
    ScannerOutput,
    TrainingDataStats,
)
from app.services.risk_classifier import RiskClassifier

GITHUB_API = "https://api.github.com"
REQUEST_TIMEOUT = 10.0
MAX_CONCURRENT_FETCHES = 5

# Files to fetch for content analysis (README + common doc files)
CONTENT_FILES: list[str] = [
    "README.md", "readme.md", "README.rst", "README",
    "docs/README.md", ".env.example",
]

# Config files to look for in the repo tree
CONFIG_FILES: list[str] = [
    "docker-compose.yml", "docker-compose.yaml",
    ".env", ".env.example", ".env.sample",
]

# Manifest files to fetch for dependency detection
MANIFEST_FILES: list[str] = [
    "requirements.txt", "pyproject.toml", "package.json",
    "Pipfile", "setup.cfg", "setup.py", "environment.yml",
    # Java
    "pom.xml", "build.gradle",
    # Go
    "go.mod",
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
        """Full multi-pass scan: tree -> manifests -> imports -> content -> config.

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
            tree_flags, tree_matched_paths = check_file_tree_flags(file_paths)

            # Pass 2: Fetch and parse manifests (search at any depth)
            manifest_files = self._find_manifest_files(file_paths, MANIFEST_FILES)
            manifest_contents = await self._fetch_files(owner, repo, branch, manifest_files)
            detected_frameworks = self._parser.parse(manifest_contents)

            # Pass 2.5: AST import scanning (always run for line-number precision)
            all_detected_imports: list[DetectedImport] = []
            py_files = select_python_files(file_paths)
            py_contents: dict[str, str] = {}
            if py_files:
                py_contents = await self._fetch_files(owner, repo, branch, py_files)
                import_frameworks: list[DetectedFramework] = []
                for filename, content in py_contents.items():
                    fws, imports = scan_python_imports_ast(content, filename=filename)
                    import_frameworks.extend(fws)
                    all_detected_imports.extend(imports)
                detected_frameworks = merge_frameworks(
                    detected_frameworks, import_frameworks,
                )

            # Pass 2.6: JS/TS import scanning (tree-sitter or regex fallback)
            js_files = select_js_files(file_paths)
            if js_files:
                js_contents = await self._fetch_files(owner, repo, branch, js_files)
                js_import_frameworks: list[DetectedFramework] = []
                for filename, content in js_contents.items():
                    fws, js_imports = scan_js_imports(content, filename=filename)
                    js_import_frameworks.extend(fws)
                    all_detected_imports.extend(js_imports)
                detected_frameworks = merge_frameworks(
                    detected_frameworks, js_import_frameworks,
                )

            # Pass 2.7: Jupyter notebook scanning (reuses import scanner)
            nb_files = select_notebook_files(file_paths)
            if nb_files:
                nb_contents = await self._fetch_files(owner, repo, branch, nb_files)
                nb_import_frameworks: list[DetectedFramework] = []
                for filename, content in nb_contents.items():
                    code_src, md_src = extract_notebook_cells(content)
                    if code_src:
                        fws, nb_imports = scan_python_imports_ast(
                            code_src, filename=filename,
                        )
                        nb_import_frameworks.extend(fws)
                        all_detected_imports.extend(nb_imports)
                    # Markdown cells added to content for keyword analysis later
                    if md_src:
                        py_contents[filename] = md_src
                detected_frameworks = merge_frameworks(
                    detected_frameworks, nb_import_frameworks,
                )

            # Pass 3: Fetch and analyze content files
            content_files = self._select_existing_files(file_paths, CONTENT_FILES)
            # Also fetch doc files discovered in tree
            doc_files = self._find_doc_files(file_paths)
            all_content_files = list(set(content_files + doc_files))
            file_contents = await self._fetch_files(owner, repo, branch, all_content_files)
            content_flags, content_matched_paths = extract_content_flags(file_contents)

            # Pass 3.5: Domain detection (zero extra API calls — reuses content)
            combined_text = "\n".join(file_contents.values())
            detected_domains = detect_domains(
                combined_text,
                has_ai_frameworks=bool(detected_frameworks),
            )

            # Pass 3.6: Doc section validation (zero extra API calls — reuses content)
            doc_validations: list[DocValidation] = []
            for filename, content in file_contents.items():
                validation = validate_doc_sections(filename, content)
                if validation is not None:
                    doc_validations.append(validation)

            # Pass 3.7: Call-chain analysis (reuses fetched .py files)
            call_chain_findings: list[CallChainFinding] = []
            if all_detected_imports and py_contents:
                ai_modules = {
                    imp.module.split(".")[0] for imp in all_detected_imports
                }
                for filename, content in py_contents.items():
                    findings = analyze_call_chains(content, filename, ai_modules)
                    call_chain_findings.extend(findings)

            # Pass 4: Config file scanning (+2-4 API calls if files exist)
            config_signals = await self._scan_config_files(
                owner, repo, branch, file_paths, file_contents,
            )

            # Merge matched paths from tree and content analysis
            all_matched_paths: dict[str, list[str]] = {}
            for field, paths in tree_matched_paths.items():
                all_matched_paths.setdefault(field, []).extend(paths)
            for field, paths in content_matched_paths.items():
                existing = all_matched_paths.get(field, [])
                all_matched_paths.setdefault(field, []).extend(
                    p for p in paths if p not in existing
                )

            output = self._build_output(
                repo_url=repo_url,
                detected_frameworks=detected_frameworks,
                tree_flags=tree_flags,
                content_flags=content_flags,
                detected_domains=detected_domains,
                config_signals=config_signals,
                doc_validations=doc_validations,
                detected_imports=all_detected_imports,
                call_chain_findings=call_chain_findings,
                matched_paths=all_matched_paths,
            )

            # Pass 5: Risk classification (uses frameworks + domains)
            classifier = RiskClassifier()
            output.risk_classification = classifier.classify(output)

            return output
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
        return matches[:30]  # Cap to avoid excessive API calls

    def _select_existing_files(
        self, tree_paths: list[str], target_files: list[str]
    ) -> list[str]:
        """Return target files that actually exist in the repo tree."""
        tree_set = {p.lower() for p in tree_paths}
        return [f for f in target_files if f.lower() in tree_set]

    async def _scan_config_files(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_paths: list[str],
        already_fetched: dict[str, str],
    ) -> list[ConfigSignal]:
        """Scan config files (env, docker-compose, terraform) for AI signals."""
        signals: list[ConfigSignal] = []

        # Find config files that exist in the tree
        config_to_fetch = self._select_existing_files(file_paths, CONFIG_FILES)
        # Find terraform files at root level (cap at 3)
        tf_files = [p for p in file_paths if p.endswith(".tf") and "/" not in p][:3]
        all_config = list(set(config_to_fetch + tf_files))

        # Separate already-fetched from needing fetch
        to_fetch = [f for f in all_config if f not in already_fetched]
        config_contents = {k: v for k, v in already_fetched.items() if k in all_config}

        if to_fetch:
            fetched = await self._fetch_files(owner, repo, branch, to_fetch)
            config_contents.update(fetched)

        for filename, content in config_contents.items():
            lower = filename.lower()
            if lower.endswith((".env", ".env.example", ".env.sample")):
                signals.extend(scan_env_content(content))
            elif "docker-compose" in lower:
                signals.extend(scan_docker_compose(content))
            elif lower.endswith(".tf"):
                signals.extend(scan_terraform(content))

        return signals

    def _find_doc_files(self, file_paths: list[str]) -> list[str]:
        """Find documentation files worth fetching for content analysis."""
        doc_patterns = [
            r"^docs/.*\.md$",
            r"^docs/.*\.rst$",
            r"^.*model.card.*$",
            r"^.*risk.assessment.*$",
            r"^compliance/.*\.md$",
            r"^ethics/.*\.md$",
            r"^safety/.*\.md$",
            r"^governance/.*\.md$",
            r"^.*fairness.*\.md$",
            r"^.*bias.*\.md$",
            r"^.*transparency.*\.md$",
        ]
        results: list[str] = []
        for path in file_paths:
            lower = path.lower()
            if any(re.match(pat, lower) for pat in doc_patterns):
                results.append(path)
        # Limit to avoid excessive fetches
        # Limit to avoid excessive fetches (increased from 10 for compliance-heavy repos)
        return results[:25]

    def _build_output(
        self,
        repo_url: str,
        detected_frameworks: list[DetectedFramework],
        tree_flags: dict[str, bool],
        content_flags: dict[str, bool | dict[str, bool]],
        detected_domains: list[DetectedDomain] | None = None,
        config_signals: list[ConfigSignal] | None = None,
        doc_validations: list[DocValidation] | None = None,
        matched_paths: dict[str, list[str]] | None = None,
        detected_imports: list[DetectedImport] | None = None,
        call_chain_findings: list[CallChainFinding] | None = None,
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
            # Article 5 prohibited practice indicators
            "has_social_scoring_indicators", "has_biometric_identification",
            "has_emotion_inference",
            # Article 50 transparency signals
            "has_ai_disclosure", "has_synthetic_content_marking",
            "has_provider_identification",
            # Phase 3 new fields (content-only, no tree patterns)
            "has_residual_risk_evaluation", "has_testing_metrics_defined",
            "has_bias_mitigation_docs", "has_data_gaps_identified",
            "has_development_process_docs", "has_standards_applied",
            "has_risk_event_logging", "has_input_data_recording",
            "has_capabilities_limitations", "has_group_performance_docs",
            "has_automation_bias_docs", "has_stop_mechanism",
            "has_cybersecurity_docs", "has_feedback_loop_prevention",
            "has_error_resilience_docs",
            # Articles 16, 17, 26, 27, 53, 55, 72 organizational/GPAI signals
            "has_contact_info", "has_impact_assessment", "has_monitoring_config",
            "has_incident_reporting", "has_copyright_policy", "has_qms_docs",
            "has_conformity_assessment",
        ]
        for field in bool_fields:
            merged[field] = bool(tree_flags.get(field)) or bool(content_flags.get(field))

        # has_escalation_docs from content rules (not inferred from oversight docs)
        merged["has_escalation_docs"] = bool(content_flags.get("has_escalation_docs"))

        # User instructions detected from file tree or content
        merged["has_user_instructions"] = bool(tree_flags.get("user_instructions_found"))

        # Phase 1B: user_instructions ≠ model_card (Art. 13 ≠ Art. 11)
        # A USAGE.md is Art. 13 (transparency), not Art. 11 (technical docs).
        # Removed: has_model_card aliasing from user_instructions_found.

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
        quality_metrics = bool(content_flags.get("quality_metrics_found"))

        training_data_stats = None
        if provenance or preprocessing or has_bias or has_data_doc or quality_metrics:
            training_data_stats = TrainingDataStats(
                provenance_documented=provenance,
                preprocessing_documented=preprocessing,
                class_balance=None,  # Phase 1A: cannot extract actual balance from file-presence
                quality_metrics_logged=quality_metrics,
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
            detected_domains=detected_domains or [],
            config_signals=config_signals or [],
            doc_validations=doc_validations or [],
            detected_imports=detected_imports or [],
            call_chain_findings=call_chain_findings or [],
            matched_paths=matched_paths or {},
        )
