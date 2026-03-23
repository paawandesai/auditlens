"""Tests for Article 50 — Transparency Obligations compliance check."""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_50 import Article50Check


class TestArticle50Check:
    """Article 50 transparency obligations check tests."""

    def test_pass_fully_compliant(self, fully_compliant_scanner_output):
        """PASS when all transparency obligations met."""
        check = Article50Check()
        result = check.evaluate(fully_compliant_scanner_output)

        assert result.status == "PASS"
        assert result.rule_id == "EU_AI_ART_50"
        assert result.article == "Article 50"
        assert result.severity == "high"
        assert all(result.details.values())
        assert result.remediation is None

    def test_fail_no_transparency(self, minimal_scanner_output):
        """FAIL when no transparency signals detected."""
        check = Article50Check()
        result = check.evaluate(minimal_scanner_output)

        assert result.status == "FAIL"
        assert not any(result.details.values())
        assert result.remediation is not None
        assert "disclosure" in result.remediation.lower()

    def test_fail_prohibited_output(self, prohibited_scanner_output):
        """FAIL on prohibited output (all Art. 50 fields are False)."""
        check = Article50Check()
        result = check.evaluate(prohibited_scanner_output)

        assert result.status == "FAIL"

    def test_partial_only_disclosure(self):
        """PARTIAL when only AI disclosure found."""
        output = ScannerOutput(
            repo_url="https://github.com/example/chatbot",
            has_ai_disclosure=True,
            has_synthetic_content_marking=False,
            has_provider_identification=False,
        )
        check = Article50Check()
        result = check.evaluate(output)

        assert result.status == "PARTIAL"
        assert result.details["ai_interaction_disclosed"] is True
        assert result.details["synthetic_content_marked"] is False
        assert result.details["provider_identified"] is False

    def test_partial_disclosure_and_provider(self):
        """PARTIAL when disclosure and provider found but no content marking."""
        output = ScannerOutput(
            repo_url="https://github.com/example/partial",
            has_ai_disclosure=True,
            has_synthetic_content_marking=False,
            has_provider_identification=True,
        )
        check = Article50Check()
        result = check.evaluate(output)

        assert result.status == "PARTIAL"
        assert result.details["ai_interaction_disclosed"] is True
        assert result.details["provider_identified"] is True

    def test_evidence_description_pass(self, fully_compliant_scanner_output):
        """Evidence mentions all obligations met on PASS."""
        check = Article50Check()
        result = check.evaluate(fully_compliant_scanner_output)

        assert "transparency obligations met" in result.evidence.description.lower()

    def test_evidence_description_fail(self, minimal_scanner_output):
        """Evidence lists gaps on FAIL."""
        check = Article50Check()
        result = check.evaluate(minimal_scanner_output)

        assert "transparency gaps" in result.evidence.description.lower()

    def test_remediation_content(self):
        """Remediation provides specific guidance for each missing item."""
        output = ScannerOutput(
            repo_url="https://github.com/example/no-transparency",
        )
        check = Article50Check()
        result = check.evaluate(output)

        assert "art. 50(1)" in result.remediation.lower()
        assert "art. 50(2)" in result.remediation.lower()
        assert "art. 50(4)" in result.remediation.lower()
