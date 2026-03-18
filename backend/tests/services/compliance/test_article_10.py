"""Tests for Article 10 — Data Governance compliance checks.

Sub-checks:
1. provenance_documented — training data sources documented
2. bias_examined — protected attributes within threshold
3. data_quality_metrics_logged — quality metrics exist
4. preprocessing_documented — data preprocessing steps recorded
"""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput, TrainingDataStats
from app.services.compliance.article_10 import Article10Check


@pytest.fixture
def check() -> Article10Check:
    return Article10Check()


class TestArticle10Metadata:
    """Test that the check has correct identification metadata."""

    def test_rule_id(self, check: Article10Check) -> None:
        assert check.rule_id == "EU_AI_ART_10"

    def test_rule_name(self, check: Article10Check) -> None:
        assert check.rule_name == "Data Governance"

    def test_article(self, check: Article10Check) -> None:
        assert check.article == "Article 10"

    def test_severity(self, check: Article10Check) -> None:
        assert check.severity == "critical"


class TestArticle10AllPass:
    """When all sub-checks pass, overall status should be PASS."""

    def test_fully_compliant_passes(
        self, check: Article10Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.status == "PASS"
        assert result.details["provenance_documented"] is True
        assert result.details["bias_examined"] is True
        assert result.details["data_quality_metrics_logged"] is True
        assert result.details["preprocessing_documented"] is True
        assert result.remediation is None


class TestArticle10AllFail:
    """When all sub-checks fail, overall status should be FAIL."""

    def test_non_compliant_fails(
        self, check: Article10Check, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(non_compliant_scanner_output)
        assert result.status == "FAIL"
        assert result.details["provenance_documented"] is False
        assert result.details["bias_examined"] is False
        assert result.details["data_quality_metrics_logged"] is False
        assert result.details["preprocessing_documented"] is False
        assert result.remediation is not None

    def test_empty_scanner_output_fails(
        self, check: Article10Check, minimal_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(minimal_scanner_output)
        assert result.status == "FAIL"
        assert result.remediation is not None


class TestArticle10Partial:
    """When some sub-checks pass and some fail, status should be PARTIAL."""

    def test_partial_compliance(
        self, check: Article10Check, partial_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(partial_scanner_output)
        assert result.status == "PARTIAL"
        assert result.details["provenance_documented"] is True
        assert result.details["preprocessing_documented"] is False
        assert result.remediation is not None


class TestArticle10ClassBalance:
    """Edge cases for class balance threshold logic."""

    def test_no_training_stats_fails_balance(
        self, check: Article10Check, minimal_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(minimal_scanner_output)
        assert result.details["bias_examined"] is False

    def test_balanced_data_passes(self, check: Article10Check) -> None:
        output = ScannerOutput(
            repo_url="https://example.com/repo",
            has_data_documentation=True,
            training_data_stats=TrainingDataStats(
                provenance_documented=True,
                class_balance={"gender": {"male": 55, "female": 45}},
                quality_metrics_logged=True,
                preprocessing_documented=True,
            ),
        )
        result = check.evaluate(output)
        assert result.details["bias_examined"] is True

    def test_severely_imbalanced_data_fails(self, check: Article10Check) -> None:
        output = ScannerOutput(
            repo_url="https://example.com/repo",
            has_data_documentation=True,
            training_data_stats=TrainingDataStats(
                provenance_documented=True,
                class_balance={"gender": {"male": 80, "female": 20}},
                quality_metrics_logged=True,
                preprocessing_documented=True,
            ),
        )
        result = check.evaluate(output)
        assert result.details["bias_examined"] is False
        imbalance = result.details.get("imbalance_details", {})
        assert "gender" in str(imbalance)

    def test_missing_class_balance_no_docs_fails(self, check: Article10Check) -> None:
        """No class balance data AND no data documentation → fail."""
        output = ScannerOutput(
            repo_url="https://example.com/repo",
            training_data_stats=TrainingDataStats(
                provenance_documented=True,
                quality_metrics_logged=True,
                preprocessing_documented=True,
            ),
        )
        result = check.evaluate(output)
        assert result.details["bias_examined"] is False

    def test_missing_class_balance_with_docs_passes(self, check: Article10Check) -> None:
        """No class balance data BUT bias/data documentation exists → pass."""
        output = ScannerOutput(
            repo_url="https://example.com/repo",
            has_data_documentation=True,
            training_data_stats=TrainingDataStats(
                provenance_documented=True,
                quality_metrics_logged=True,
                preprocessing_documented=True,
            ),
        )
        result = check.evaluate(output)
        assert result.details["bias_examined"] is True

    def test_multiple_protected_attributes(self, check: Article10Check) -> None:
        """If any protected attribute is imbalanced, bias_examined is False."""
        output = ScannerOutput(
            repo_url="https://example.com/repo",
            has_data_documentation=True,
            training_data_stats=TrainingDataStats(
                provenance_documented=True,
                class_balance={
                    "gender": {"male": 52, "female": 48},
                    "ethnicity": {"group_a": 90, "group_b": 10},
                },
                quality_metrics_logged=True,
                preprocessing_documented=True,
            ),
        )
        result = check.evaluate(output)
        assert result.details["bias_examined"] is False


class TestArticle10EvidenceFormat:
    """Verify evidence structure matches the schema."""

    def test_evidence_has_required_fields(
        self, check: Article10Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.evidence.description
        assert result.evidence.source
        assert result.evidence.checked_at is not None

    def test_rule_id_matches(
        self, check: Article10Check, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = check.evaluate(fully_compliant_scanner_output)
        assert result.rule_id == "EU_AI_ART_10"
        assert result.article == "Article 10"
