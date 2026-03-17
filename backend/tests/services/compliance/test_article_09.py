"""Tests for Article 9 — Risk Management System compliance checks.

Sub-checks:
1. risk_assessment_exists — risk assessment documentation found
2. failure_modes_cataloged — failure modes identified and documented
3. mitigation_documented — risk mitigation measures documented
"""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_09 import Article09Check


@pytest.fixture
def check() -> Article09Check:
    return Article09Check()


class TestArticle09Metadata:
    def test_rule_id(self, check: Article09Check) -> None:
        assert check.rule_id == "EU_AI_ART_9"

    def test_severity(self, check: Article09Check) -> None:
        assert check.severity == "critical"


class TestArticle09AllPass:
    def test_fully_compliant(
        self, check: Article09Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.status == "PASS"
        assert result.details["risk_assessment_exists"] is True
        assert result.details["failure_modes_cataloged"] is True
        assert result.details["mitigation_documented"] is True
        assert result.remediation is None


class TestArticle09AllFail:
    def test_non_compliant(
        self, check: Article09Check, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(non_compliant_scanner_output)
        assert result.status == "FAIL"
        assert result.remediation is not None

    def test_empty_output(
        self, check: Article09Check, minimal_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(minimal_scanner_output)
        assert result.status == "FAIL"


class TestArticle09Partial:
    def test_partial_compliance(
        self, check: Article09Check, partial_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(partial_scanner_output)
        # partial has risk_assessment=True but no performance_metrics for failure modes
        assert result.status in ("PASS", "PARTIAL")
