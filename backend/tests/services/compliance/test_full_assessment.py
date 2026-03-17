"""Integration tests — full ComplianceEngine with all 7 article checks.

Verifies the engine produces correct AssessmentResult matching the
JSON schema from CLAUDE.md Section 6.
"""

from __future__ import annotations

from app.schemas.scanner import ScannerOutput
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


def _make_engine() -> ComplianceEngine:
    return ComplianceEngine(ALL_CHECKS)


class TestFullAssessmentStructure:
    """Verify the full assessment output has the expected shape."""

    def test_all_seven_articles_evaluated(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(fully_compliant_scanner_output)
        assert result.summary.total_checks == 7
        rule_ids = {c.rule_id for c in result.checks}
        assert rule_ids == {
            "EU_AI_ART_9",
            "EU_AI_ART_10",
            "EU_AI_ART_11",
            "EU_AI_ART_12",
            "EU_AI_ART_13",
            "EU_AI_ART_14",
            "EU_AI_ART_15",
        }

    def test_schema_version_present(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(fully_compliant_scanner_output)
        assert result.schema_version == "1.0"

    def test_assessment_id_is_uuid(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        import uuid

        result = _make_engine().run(fully_compliant_scanner_output)
        uuid.UUID(result.assessment_id)  # raises if not valid UUID

    def test_generated_at_present(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(fully_compliant_scanner_output)
        assert result.generated_at is not None


class TestFullyCompliantAssessment:
    """A well-documented system should be COMPLIANT."""

    def test_overall_compliant(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(fully_compliant_scanner_output)
        assert result.summary.overall_status == "COMPLIANT"
        assert result.summary.passed == 7
        assert result.summary.failed == 0
        assert result.summary.partial == 0
        assert result.summary.compliance_score == 100
        assert result.summary.critical_failures == []

    def test_no_remediation_needed(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(fully_compliant_scanner_output)
        for check in result.checks:
            assert check.remediation is None


class TestNonCompliantAssessment:
    """A poorly documented system should be NON_COMPLIANT."""

    def test_overall_non_compliant(
        self, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(non_compliant_scanner_output)
        assert result.summary.overall_status == "NON_COMPLIANT"
        assert result.summary.failed > 0
        assert result.summary.compliance_score < 50

    def test_critical_failures_identified(
        self, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(non_compliant_scanner_output)
        # Articles 9, 10, 11, 14 are critical severity and should fail
        assert len(result.summary.critical_failures) >= 3

    def test_all_failed_checks_have_remediation(
        self, non_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(non_compliant_scanner_output)
        for check in result.checks:
            if check.status in ("FAIL", "PARTIAL"):
                assert check.remediation is not None
                assert len(check.remediation) > 0


class TestPartialAssessment:
    """A partially documented system should be PARTIALLY_COMPLIANT or NON_COMPLIANT."""

    def test_mixed_results(self, partial_scanner_output: ScannerOutput) -> None:
        result = _make_engine().run(partial_scanner_output)
        assert result.summary.overall_status in ("NON_COMPLIANT", "PARTIALLY_COMPLIANT")
        assert 0 < result.summary.compliance_score < 100


class TestEmptyRepoAssessment:
    """An empty repo should fail everything."""

    def test_all_fail(self, minimal_scanner_output: ScannerOutput) -> None:
        result = _make_engine().run(minimal_scanner_output)
        assert result.summary.overall_status == "NON_COMPLIANT"
        assert result.summary.failed == 7
        assert result.summary.compliance_score == 0


class TestJsonSerialization:
    """Verify the output can be serialized to JSON matching CLAUDE.md Section 6."""

    def test_serializes_to_json(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        result = _make_engine().run(fully_compliant_scanner_output)
        json_str = result.model_dump_json()
        assert '"schema_version"' in json_str
        assert '"assessment_id"' in json_str
        assert '"checks"' in json_str
        assert '"summary"' in json_str

    def test_roundtrip_json(
        self, fully_compliant_scanner_output: ScannerOutput
    ) -> None:
        from app.schemas.compliance import AssessmentResult

        result = _make_engine().run(fully_compliant_scanner_output)
        json_str = result.model_dump_json()
        restored = AssessmentResult.model_validate_json(json_str)
        assert restored.summary.total_checks == result.summary.total_checks
        assert len(restored.checks) == len(result.checks)
