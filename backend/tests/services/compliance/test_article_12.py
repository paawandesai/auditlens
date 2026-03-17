"""Tests for Article 12 — Record-Keeping compliance checks.

Sub-checks:
1. logging_configured — logging/monitoring is set up
2. model_versioned — model versioning is in place
3. audit_trail_exists — audit trail for decisions exists
"""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_12 import Article12Check


@pytest.fixture
def check() -> Article12Check:
    return Article12Check()


class TestArticle12Metadata:
    def test_rule_id(self, check: Article12Check) -> None:
        assert check.rule_id == "EU_AI_ART_12"

    def test_severity(self, check: Article12Check) -> None:
        assert check.severity == "high"


class TestArticle12AllPass:
    def test_fully_compliant(
        self, check: Article12Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.status == "PASS"
        assert result.details["logging_configured"] is True
        assert result.details["model_versioned"] is True
        assert result.details["audit_trail_exists"] is True


class TestArticle12AllFail:
    def test_non_compliant(
        self, check: Article12Check, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(non_compliant_scanner_output)
        assert result.status == "FAIL"

    def test_empty_output(
        self, check: Article12Check, minimal_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(minimal_scanner_output)
        assert result.status == "FAIL"
