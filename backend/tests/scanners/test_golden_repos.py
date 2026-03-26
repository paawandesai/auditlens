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

    @pytest.mark.asyncio
    async def test_employment_domain_detected(self):
        """Hiring AI should detect employment domain (category 4a/4b/4c)."""
        output, _ = await _scan_and_assess(self.REPO)
        categories = {d.annex_iii_category for d in output.detected_domains}
        cat4 = {c for c in categories if c.startswith("4")}
        assert len(cat4) >= 1, f"Expected employment domain, got categories: {categories}"

    @pytest.mark.asyncio
    async def test_risk_level_high_or_limited(self):
        """Hiring AI with ML frameworks should be HIGH or LIMITED risk."""
        output, _ = await _scan_and_assess(self.REPO)
        assert output.risk_classification is not None
        assert output.risk_classification.risk_level in ("HIGH", "LIMITED"), (
            f"Expected HIGH/LIMITED, got {output.risk_classification.risk_level}"
        )


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

    @pytest.mark.asyncio
    async def test_no_domains_detected(self):
        """Non-ML repo should have zero Annex III domain detections."""
        output, _ = await _scan_and_assess(self.REPO)
        assert len(output.detected_domains) == 0, (
            f"False positive domains: {[d.domain for d in output.detected_domains]}"
        )


# ---------------------------------------------------------------------------
# Golden Repo 5: vercel/ai-chatbot — JS/TS AI project (package.json path)
# ---------------------------------------------------------------------------
# Next.js chatbot using Vercel AI SDK. Tests the JavaScript framework detection
# path (package.json parsing) — our other 4 golden repos are Python.
# Expected: AI frameworks detected from package.json, all compliance checks FAIL
# (no compliance docs), zero false-positive Python framework detections.

class TestVercelAIChatbot:
    REPO = "https://github.com/vercel/ai-chatbot"

    @pytest.mark.asyncio
    async def test_js_frameworks_detected(self):
        """Should detect AI SDK packages from package.json."""
        output, _ = await _scan_and_assess(self.REPO)
        names = {f.name for f in output.detected_frameworks}
        assert len(names) >= 1, f"Expected 1+ JS AI frameworks, got: {names}"
        # The 'ai' package (Vercel AI SDK) should always be present
        assert "ai" in names, f"Expected 'ai' in detected frameworks: {names}"

    @pytest.mark.asyncio
    async def test_no_python_false_positives(self):
        """A JS-only repo should not detect Python ML frameworks."""
        output, _ = await _scan_and_assess(self.REPO)
        python_ml = {"scikit-learn", "tensorflow", "pytorch", "keras", "pandas",
                     "numpy", "xgboost", "lightgbm", "transformers"}
        detected = {f.name for f in output.detected_frameworks}
        false_positives = detected & python_ml
        assert len(false_positives) == 0, f"Python false positives: {false_positives}"

    @pytest.mark.asyncio
    async def test_all_articles_fail(self):
        """No compliance docs → all articles should FAIL."""
        _, assessment = await _scan_and_assess(self.REPO)
        checks = _check_map(assessment)
        for rule_id, check in checks.items():
            assert check.status == "FAIL", f"{rule_id} expected FAIL, got {check.status}"

    @pytest.mark.asyncio
    async def test_overall_non_compliant(self):
        _, assessment = await _scan_and_assess(self.REPO)
        assert assessment.summary.overall_status == "NON_COMPLIANT"

    @pytest.mark.asyncio
    async def test_no_employment_domain(self):
        """Chatbot should NOT trigger employment domain detection."""
        output, _ = await _scan_and_assess(self.REPO)
        employment_domains = [
            d for d in output.detected_domains
            if d.annex_iii_category.startswith("4")
        ]
        assert len(employment_domains) == 0, (
            f"False positive employment domains: "
            f"{[(d.domain, d.matched_keywords) for d in employment_domains]}"
        )


# ---------------------------------------------------------------------------
# Golden Repo 6: jakevdp/PythonDataScienceHandbook — Pure DS (false positive guard)
# ---------------------------------------------------------------------------
# Textbook repo using scikit-learn, pandas, numpy, matplotlib heavily.
# Zero employment keywords. Tests that ML frameworks alone don't trigger
# employment domain detection via contextual boosting (false positive guard).

class TestDataScienceHandbook:
    REPO = "https://github.com/jakevdp/PythonDataScienceHandbook"

    @pytest.mark.asyncio
    async def test_ml_frameworks_detected(self):
        """Should detect ML frameworks from imports/notebooks."""
        output, _ = await _scan_and_assess(self.REPO)
        names = {f.name for f in output.detected_frameworks}
        assert len(names) >= 1, f"Expected 1+ ML frameworks, got: {names}"

    @pytest.mark.asyncio
    async def test_no_employment_domain(self):
        """Pure data science repo should NOT trigger employment domain."""
        output, _ = await _scan_and_assess(self.REPO)
        employment_domains = [
            d for d in output.detected_domains
            if d.annex_iii_category.startswith("4")
        ]
        assert len(employment_domains) == 0, (
            f"False positive employment domains: "
            f"{[(d.domain, d.matched_keywords) for d in employment_domains]}"
        )

    @pytest.mark.asyncio
    async def test_risk_not_high(self):
        """DS textbook should NOT be classified as HIGH risk."""
        output, _ = await _scan_and_assess(self.REPO)
        if output.risk_classification:
            assert output.risk_classification.risk_level != "HIGH", (
                f"False positive HIGH risk for a textbook repo: "
                f"score={output.risk_classification.risk_score}"
            )
