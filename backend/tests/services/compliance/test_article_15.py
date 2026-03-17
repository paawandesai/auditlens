"""Tests for Article 15 — Accuracy, Robustness, Cybersecurity compliance checks.

Sub-checks:
1. test_metrics_logged — test set performance metrics are logged
2. adversarial_tested — adversarial robustness has been tested
3. versioning_in_place — model versioning exists
"""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_15 import Article15Check


@pytest.fixture
def check() -> Article15Check:
    return Article15Check()


class TestArticle15Metadata:
    def test_rule_id(self, check: Article15Check) -> None:
        assert check.rule_id == "EU_AI_ART_15"

    def test_severity(self, check: Article15Check) -> None:
        assert check.severity == "high"


class TestArticle15AllPass:
    def test_fully_compliant(
        self, check: Article15Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.status == "PASS"
        assert result.details["test_metrics_logged"] is True
        assert result.details["adversarial_tested"] is True
        assert result.details["versioning_in_place"] is True


class TestArticle15AllFail:
    def test_non_compliant(
        self, check: Article15Check, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(non_compliant_scanner_output)
        assert result.status == "FAIL"
        assert result.remediation is not None


class TestArticle15Partial:
    def test_partial(
        self, check: Article15Check, partial_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(partial_scanner_output)
        # partial has versioning=True, has_test_suite=False, adversarial_tested=False
        assert result.status == "PARTIAL"
