"""Tests for Article 5 — Prohibited AI Practices compliance check."""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_05 import Article05Check


class TestArticle05Check:
    """Article 5 prohibited practices check tests."""

    def test_pass_no_indicators(self, fully_compliant_scanner_output):
        """PASS when no prohibited practice indicators detected."""
        check = Article05Check()
        result = check.evaluate(fully_compliant_scanner_output)

        assert result.status == "PASS"
        assert result.rule_id == "EU_AI_ART_5"
        assert result.article == "Article 5"
        assert result.severity == "critical"
        assert all(result.details.values())
        assert result.remediation is None

    def test_fail_all_indicators(self, prohibited_scanner_output):
        """FAIL when all prohibited practice indicators detected."""
        check = Article05Check()
        result = check.evaluate(prohibited_scanner_output)

        assert result.status == "FAIL"
        assert not any(result.details.values())
        assert result.remediation is not None
        assert "social scoring" in result.remediation.lower()
        assert "biometric" in result.remediation.lower()
        assert "emotion" in result.remediation.lower()

    def test_partial_social_scoring_only(self):
        """PARTIAL when only social scoring indicators detected."""
        output = ScannerOutput(
            repo_url="https://github.com/example/social-scoring",
            has_social_scoring_indicators=True,
            has_biometric_identification=False,
            has_emotion_inference=False,
        )
        check = Article05Check()
        result = check.evaluate(output)

        assert result.status == "PARTIAL"
        assert result.details["no_social_scoring"] is False
        assert result.details["no_biometric_categorisation"] is True
        assert result.details["no_emotion_inference"] is True

    def test_partial_biometric_only(self):
        """PARTIAL when only biometric identification indicators detected."""
        output = ScannerOutput(
            repo_url="https://github.com/example/biometric",
            has_biometric_identification=True,
        )
        check = Article05Check()
        result = check.evaluate(output)

        assert result.status == "PARTIAL"
        assert result.details["no_biometric_categorisation"] is False

    def test_partial_emotion_only(self):
        """PARTIAL when only emotion inference indicators detected."""
        output = ScannerOutput(
            repo_url="https://github.com/example/emotion",
            has_emotion_inference=True,
        )
        check = Article05Check()
        result = check.evaluate(output)

        assert result.status == "PARTIAL"
        assert result.details["no_emotion_inference"] is False

    def test_pass_minimal_output(self, minimal_scanner_output):
        """PASS on minimal output (no indicators = clean)."""
        check = Article05Check()
        result = check.evaluate(minimal_scanner_output)

        assert result.status == "PASS"

    def test_evidence_description_pass(self, fully_compliant_scanner_output):
        """Evidence description mentions no prohibited indicators on PASS."""
        check = Article05Check()
        result = check.evaluate(fully_compliant_scanner_output)

        assert "no prohibited" in result.evidence.description.lower()

    def test_evidence_description_fail(self, prohibited_scanner_output):
        """Evidence description lists violations on FAIL."""
        check = Article05Check()
        result = check.evaluate(prohibited_scanner_output)

        assert "prohibited practice indicators" in result.evidence.description.lower()
