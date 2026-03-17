"""Tests for Article 11 — Technical Documentation compliance checks.

Sub-checks:
1. model_card_exists — model card documentation found
2. architecture_documented — system architecture is documented
3. performance_recorded — performance metrics are recorded
"""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_11 import Article11Check


@pytest.fixture
def check() -> Article11Check:
    return Article11Check()


class TestArticle11Metadata:
    def test_rule_id(self, check: Article11Check) -> None:
        assert check.rule_id == "EU_AI_ART_11"

    def test_severity(self, check: Article11Check) -> None:
        assert check.severity == "critical"


class TestArticle11AllPass:
    def test_fully_compliant(
        self, check: Article11Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.status == "PASS"
        assert result.details["model_card_exists"] is True
        assert result.details["architecture_documented"] is True
        assert result.details["performance_recorded"] is True


class TestArticle11AllFail:
    def test_non_compliant(
        self, check: Article11Check, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(non_compliant_scanner_output)
        assert result.status == "FAIL"
        assert result.remediation is not None

    def test_empty_output(
        self, check: Article11Check, minimal_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(minimal_scanner_output)
        assert result.status == "FAIL"


class TestArticle11Partial:
    def test_model_card_only(self, check: Article11Check) -> None:
        output = ScannerOutput(
            repo_url="https://example.com/repo",
            has_model_card=True,
            has_architecture_docs=False,
        )
        result = check.evaluate(output)
        assert result.status == "PARTIAL"
        assert result.details["model_card_exists"] is True
        assert result.details["architecture_documented"] is False
        assert result.details["performance_recorded"] is False
