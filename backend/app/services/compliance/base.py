"""Base compliance check protocol and engine.

The engine orchestrates all article checks and produces an AssessmentResult.
Each article check is a standalone class implementing the ArticleCheck protocol.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.schemas.compliance import (
    AssessmentResult,
    ComplianceCheck,
    ComplianceSummary,
    SeverityLiteral,
)
from app.schemas.scanner import ScannerOutput


@runtime_checkable
class ArticleCheck(Protocol):
    """Protocol that every article check must satisfy."""

    rule_id: str
    rule_name: str
    article: str
    severity: SeverityLiteral

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck: ...


class ComplianceEngine:
    """Runs all registered article checks and produces an AssessmentResult.

    Pure orchestration — no side effects. Iterates checks, collects results,
    computes summary statistics.
    """

    def __init__(self, checks: Sequence[ArticleCheck]) -> None:
        self._checks = list(checks)

    def run(self, scanner_output: ScannerOutput) -> AssessmentResult:
        """Execute all checks against scanner output and return full assessment."""
        results = [check.evaluate(scanner_output) for check in self._checks]
        summary = self._compute_summary(results)
        return AssessmentResult(checks=results, summary=summary)

    def run_advisory(self, scanner_output: ScannerOutput) -> list[ComplianceCheck]:
        """Run checks for informational purposes only (not scored)."""
        return [check.evaluate(scanner_output) for check in self._checks]

    def _compute_summary(self, checks: list[ComplianceCheck]) -> ComplianceSummary:
        """Compute aggregate statistics from individual check results."""
        total = len(checks)
        passed = sum(1 for c in checks if c.status == "PASS")
        failed = sum(1 for c in checks if c.status == "FAIL")
        partial = sum(1 for c in checks if c.status == "PARTIAL")

        critical_failures = [
            c.rule_id for c in checks if c.status == "FAIL" and c.severity == "critical"
        ]

        score = self._compute_score(checks) if total > 0 else 0

        if failed == 0 and partial == 0:
            overall = "COMPLIANT"
        elif failed > 0:
            overall = "NON_COMPLIANT"
        else:
            overall = "PARTIALLY_COMPLIANT"

        return ComplianceSummary(
            total_checks=total,
            passed=passed,
            failed=failed,
            partial=partial,
            compliance_score=score,
            overall_status=overall,
            critical_failures=critical_failures,
        )

    def _compute_score(self, checks: list[ComplianceCheck]) -> int:
        """Weighted compliance score (0-100).

        Critical checks count double. PASS=1.0, PARTIAL=0.5, FAIL=0.0.
        """
        severity_weight: dict[str, float] = {
            "critical": 2.0,
            "high": 1.5,
            "medium": 1.0,
            "low": 0.5,
        }
        status_score = {"PASS": 1.0, "PARTIAL": 0.5, "FAIL": 0.0}

        total_weight = sum(severity_weight[c.severity] for c in checks)
        earned = sum(
            severity_weight[c.severity] * status_score[c.status] for c in checks
        )

        return round((earned / total_weight) * 100) if total_weight > 0 else 0
