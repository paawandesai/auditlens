"""Tests for Article 13 — Transparency compliance checks.

Sub-checks:
1. explainability_available — SHAP/LIME or similar available
2. feature_importance_documented — feature importance is documented
3. user_instructions_provided — instructions for use exist
"""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_13 import Article13Check


@pytest.fixture
def check() -> Article13Check:
    return Article13Check()


class TestArticle13Metadata:
    def test_rule_id(self, check: Article13Check) -> None:
        assert check.rule_id == "EU_AI_ART_13"

    def test_severity(self, check: Article13Check) -> None:
        assert check.severity == "high"


class TestArticle13AllPass:
    def test_fully_compliant(
        self, check: Article13Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.status == "PASS"
        assert result.details["explainability_available"] is True
        assert result.details["feature_importance_documented"] is True
        assert result.details["user_instructions_provided"] is True


class TestArticle13AllFail:
    def test_non_compliant(
        self, check: Article13Check, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(non_compliant_scanner_output)
        assert result.status == "FAIL"
        assert result.remediation is not None


class TestArticle13Partial:
    def test_partial(
        self, check: Article13Check, partial_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(partial_scanner_output)
        # partial has has_explainability=False, model_card=True
        assert result.status == "PARTIAL"
