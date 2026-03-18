"""Golden repo tests — validate scanner against real public GitHub repos.

These tests hit the live GitHub API and verify that the full pipeline
(GitHubScanner → ContentAnalyzer → ComplianceEngine) produces expected
results for repos with known compliance characteristics.

Run manually:  GITHUB_TOKEN=ghp_xxx pytest tests/scanners/test_golden_repos.py -v --run-golden
Skip in CI:    these tests are skipped by default (require --run-golden flag)

Requires GITHUB_TOKEN env var to avoid rate limiting (each repo scan ~10-20 API calls).
"""

from __future__ import annotations

import os

import pytest

from app.scanners.github_scanner import GitHubScanner
from app.services.compliance.article_09 import Article09Check
from app.services.compliance.article_10 import Article10Check
from app.services.compliance.article_11 import Article11Check
from app.services.compliance.article_12 import Article12Check
from app.services.compliance.article_13 import Article13Check
from app.services.compliance.article_14 import Article14Check
from app.services.compliance.article_15 import Article15Check
from app.services.compliance.base import ComplianceEngine

ALL_CHECKS = [
    Article09Check(),
    Article10Check(),
    Article11Check(),
    Article12Check(),
    Article13Check(),
    Article14Check(),
    Article15Check(),
]

pytestmark = [
    pytest.mark.golden,
    pytest.mark.skipif(
        not os.environ.get("GITHUB_TOKEN"),
        reason="GITHUB_TOKEN required for golden tests",
    ),
]


def _check_map(assessment):
    """Build rule_id → ComplianceCheck map from assessment."""
    return {c.rule_id: c for c in assessment.checks}


# Module-level cache so each repo is scanned only once across all tests.
_cache: dict[str, tuple] = {}


async def _scan_and_assess(repo_url: str):
    """Run full pipeline with caching — one API round-trip per repo."""
    if repo_url not in _cache:
        scanner = GitHubScanner()
        output = await scanner.scan(repo_url)
        engine = ComplianceEngine(ALL_CHECKS)
        assessment = engine.run(output)
        _cache[repo_url] = (output, assessment)
    return _cache[repo_url]


# ---------------------------------------------------------------------------
# Golden Repo 1: Trusted-AI/AIF360 — Well-documented fairness toolkit
# ---------------------------------------------------------------------------
# IBM's AI Fairness 360. Has fairness/bias substance, tests, docs, but
# few formal compliance files (no MODEL_CARD, no RISK_ASSESSMENT standalone).
# Expected: Mostly PARTIAL or FAIL, definitely not COMPLIANT.

class TestAIF360:
    REPO = "https://github.com/Trusted-AI/AIF360"

    @pytest.mark.asyncio
    async def test_frameworks_detected(self):
        output, _ = await _scan_and_assess(self.REPO)
        names = {f.name for f in output.detected_frameworks}
        assert len(names) >= 2, f"Expected 2+ frameworks, got: {names}"

    @pytest.mark.asyncio
    async def test_has_test_suite(self):
        output, _ = await _scan_and_assess(self.REPO)
        assert output.has_test_suite is True

    @pytest.mark.asyncio
    async def test_art9_risk_management(self):
        """No standalone risk assessment file → expect FAIL or PARTIAL."""
        _, assessment = await _scan_and_assess(self.REPO)
        checks = _check_map(assessment)
        assert checks["EU_AI_ART_9"].status in ("FAIL", "PARTIAL")

    @pytest.mark.asyncio
    async def test_art15_has_test_suite_signal(self):
        """Has tests/ → Art 15 should be at least PARTIAL."""
        _, assessment = await _scan_and_assess(self.REPO)
        checks = _check_map(assessment)
        assert checks["EU_AI_ART_15"].status in ("PASS", "PARTIAL")

    @pytest.mark.asyncio
    async def test_overall_not_fully_compliant(self):
        """Even a well-documented repo lacks formal compliance files."""
        _, assessment = await _scan_and_assess(self.REPO)
        assert assessment.summary.overall_status in ("NON_COMPLIANT", "PARTIALLY_COMPLIANT")


# ---------------------------------------------------------------------------
# Golden Repo 2: krishnabadhautiya/Smart_Hire_AI — Hiring AI, zero docs
# ---------------------------------------------------------------------------
# Real hiring AI with heavy ML (transformers, sklearn, langchain, openai)
# but zero compliance documentation. Annex III Category 4a.
# Expected: All or nearly all FAIL.

class TestSmartHireAI:
    REPO = "https://github.com/krishnabadhautiya/Smart_Hire_AI"

    @pytest.mark.asyncio
    async def test_frameworks_detected(self):
        output, _ = await _scan_and_assess(self.REPO)
        names = {f.name for f in output.detected_frameworks}
        assert len(names) >= 3, f"Expected 3+ frameworks, got: {names}"

    @pytest.mark.asyncio
    async def test_mostly_failing(self):
        """A hiring AI with no compliance docs should fail most checks."""
        _, assessment = await _scan_and_assess(self.REPO)
        checks = _check_map(assessment)
        fail_count = sum(1 for c in checks.values() if c.status == "FAIL")
        assert fail_count >= 5, (
            f"Expected >=5 FAILs, got {fail_count}: "
            + ", ".join(f"{k}={v.status}" for k, v in checks.items())
        )

    @pytest.mark.asyncio
    async def test_overall_non_compliant(self):
        _, assessment = await _scan_and_assess(self.REPO)
        assert assessment.summary.overall_status == "NON_COMPLIANT"


# ---------------------------------------------------------------------------
# Golden Repo 3: Srishtisharma7/ResumeScreener — Bare 2-file repo
# ---------------------------------------------------------------------------
# Just README.md + Resume_screener.py. No requirements.txt, no tests,
# no docs. Uses sklearn inline.
# Expected: All FAIL.

class TestResumeScreener:
    REPO = "https://github.com/Srishtisharma7/ResumeScreener-and-CandidateRanking-"

    @pytest.mark.asyncio
    async def test_scan_succeeds(self):
        """Scanner should handle a 2-file repo without errors."""
        output, _ = await _scan_and_assess(self.REPO)
        assert output.repo_url is not None

    @pytest.mark.asyncio
    async def test_all_fail(self):
        """With no docs at all, every article should FAIL."""
        _, assessment = await _scan_and_assess(self.REPO)
        checks = _check_map(assessment)
        for rule_id, check in checks.items():
            assert check.status == "FAIL", f"{rule_id} expected FAIL, got {check.status}"

    @pytest.mark.asyncio
    async def test_overall_non_compliant(self):
        _, assessment = await _scan_and_assess(self.REPO)
        assert assessment.summary.overall_status == "NON_COMPLIANT"
        assert assessment.summary.compliance_score < 20


# ---------------------------------------------------------------------------
# Golden Repo 4: pallets/flask — Non-ML repo (negative test)
# ---------------------------------------------------------------------------
# Major Python web framework with extensive docs/tests — but zero ML.
# Verifies no false positive AI framework detections.
# Expected: No AI systems detected, all checks FAIL (nothing to assess).

class TestFlask:
    REPO = "https://github.com/pallets/flask"

    @pytest.mark.asyncio
    async def test_no_ml_frameworks(self):
        """Flask should have zero ML/AI framework detections."""
        output, _ = await _scan_and_assess(self.REPO)
        ml_names = {f.name for f in output.detected_frameworks}
        assert len(ml_names) == 0, f"False positive frameworks: {ml_names}"

    @pytest.mark.asyncio
    async def test_overall_non_compliant_but_no_ai(self):
        """With no AI detected, all checks fail — but that's expected."""
        _, assessment = await _scan_and_assess(self.REPO)
        assert assessment.summary.overall_status == "NON_COMPLIANT"
