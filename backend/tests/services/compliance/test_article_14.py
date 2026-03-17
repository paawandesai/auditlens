"""Tests for Article 14 — Human Oversight compliance checks.

Sub-checks:
1. human_in_loop_documented — human-in-the-loop mechanism documented
2. override_capability — human override capability exists
3. escalation_procedures — escalation procedures documented
"""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_14 import Article14Check


@pytest.fixture
def check() -> Article14Check:
    return Article14Check()


class TestArticle14Metadata:
    def test_rule_id(self, check: Article14Check) -> None:
        assert check.rule_id == "EU_AI_ART_14"

    def test_severity(self, check: Article14Check) -> None:
        assert check.severity == "critical"


class TestArticle14AllPass:
    def test_fully_compliant(
        self, check: Article14Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.status == "PASS"
        assert result.details["human_in_loop_documented"] is True
        assert result.details["override_capability"] is True
        assert result.details["escalation_procedures"] is True


class TestArticle14AllFail:
    def test_non_compliant(
        self, check: Article14Check, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(non_compliant_scanner_output)
        assert result.status == "FAIL"
        assert result.remediation is not None

    def test_empty_output(
        self, check: Article14Check, minimal_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(minimal_scanner_output)
        assert result.status == "FAIL"


class TestArticle14Partial:
    def test_docs_without_risk_assessment(self, check: Article14Check) -> None:
        """Oversight docs present but no risk assessment — override/escalation can't be verified."""
        output = ScannerOutput(
            repo_url="https://example.com/repo",
            has_human_oversight_docs=True,
            has_risk_assessment=False,
        )
        result = check.evaluate(output)
        assert result.status == "PARTIAL"
        assert result.details["human_in_loop_documented"] is True
        assert result.details["override_capability"] is False
