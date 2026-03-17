"""Tests for the ComplianceEngine — orchestration and summary computation."""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck
from app.schemas.scanner import ScannerOutput
from app.services.compliance.base import ComplianceEngine


class FakePassCheck:
    """A fake check that always passes."""

    rule_id = "FAKE_PASS"
    rule_name = "Fake Pass"
    article = "Article X"
    severity = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status="PASS",
            severity=self.severity,
            evidence=CheckEvidence(description="All good", source="test"),
            details={"ok": True},
        )


class FakeFailCheck:
    """A fake check that always fails."""

    rule_id = "FAKE_FAIL"
    rule_name = "Fake Fail"
    article = "Article Y"
    severity = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status="FAIL",
            severity=self.severity,
            evidence=CheckEvidence(description="Not good", source="test"),
            details={"ok": False},
            remediation="Fix it",
        )


class FakePartialCheck:
    """A fake check that returns PARTIAL."""

    rule_id = "FAKE_PARTIAL"
    rule_name = "Fake Partial"
    article = "Article Z"
    severity = "medium"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status="PARTIAL",
            severity=self.severity,
            evidence=CheckEvidence(description="Partially there", source="test"),
            details={"ok": "partial"},
            remediation="Improve it",
        )


class TestEngineRun:
    """Test the engine runs all checks and collects results."""

    def test_runs_all_checks(self, minimal_scanner_output: ScannerOutput) -> None:
        engine = ComplianceEngine([FakePassCheck(), FakeFailCheck()])
        result = engine.run(minimal_scanner_output)
        assert len(result.checks) == 2

    def test_empty_checks(self, minimal_scanner_output: ScannerOutput) -> None:
        engine = ComplianceEngine([])
        result = engine.run(minimal_scanner_output)
        assert len(result.checks) == 0
        assert result.summary.total_checks == 0

    def test_assessment_has_id_and_version(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([FakePassCheck()])
        result = engine.run(minimal_scanner_output)
        assert result.schema_version == "1.0"
        assert result.assessment_id  # non-empty UUID string


class TestEngineSummary:
    """Test summary computation logic."""

    def test_all_pass_is_compliant(self, minimal_scanner_output: ScannerOutput) -> None:
        engine = ComplianceEngine([FakePassCheck(), FakePassCheck()])
        result = engine.run(minimal_scanner_output)
        assert result.summary.overall_status == "COMPLIANT"
        assert result.summary.passed == 2
        assert result.summary.failed == 0
        assert result.summary.compliance_score == 100

    def test_any_fail_is_non_compliant(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([FakePassCheck(), FakeFailCheck()])
        result = engine.run(minimal_scanner_output)
        assert result.summary.overall_status == "NON_COMPLIANT"
        assert result.summary.failed == 1

    def test_partial_only_is_partially_compliant(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([FakePassCheck(), FakePartialCheck()])
        result = engine.run(minimal_scanner_output)
        assert result.summary.overall_status == "PARTIALLY_COMPLIANT"

    def test_critical_failures_tracked(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        engine = ComplianceEngine([FakeFailCheck()])
        result = engine.run(minimal_scanner_output)
        assert "FAKE_FAIL" in result.summary.critical_failures

    def test_non_critical_fail_not_in_critical_failures(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        """A high-severity fail should not appear in critical_failures."""

        class HighFailCheck(FakeFailCheck):
            rule_id = "HIGH_FAIL"
            severity = "high"

        engine = ComplianceEngine([HighFailCheck()])
        result = engine.run(minimal_scanner_output)
        assert result.summary.critical_failures == []

    def test_score_weights_severity(
        self, minimal_scanner_output: ScannerOutput
    ) -> None:
        """Critical fail + high pass should produce a score between 0 and 100."""
        engine = ComplianceEngine([FakeFailCheck(), FakePassCheck()])
        result = engine.run(minimal_scanner_output)
        # critical=2.0 weight fail + high=1.5 weight pass
        # earned = 0 + 1.5 = 1.5, total = 3.5 → 1.5/3.5 ≈ 43
        assert 0 < result.summary.compliance_score < 100
        assert result.summary.compliance_score == round((1.5 / 3.5) * 100)
