"""Base compliance check protocol and engine.

The engine orchestrates all article checks and produces an AssessmentResult.
Each article check is a standalone class implementing the ArticleCheck protocol.

Role-based applicability
------------------------
`run(scanner_output, role)` consults `applicability.is_applicable(article, role)`
before evaluating each check. Non-applicable articles produce an `N/A` result
that does not contribute to the compliance score and is not surfaced in the
Critical Failures banner. The default role is "undeclared", which scores
universal and provider-side articles but never deployer-only (Art. 26, 27)
or GPAI-model (Art. 53, 55) obligations.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.schemas.compliance import (
    AssessmentResult,
    CheckEvidence,
    ComplianceCheck,
    ComplianceSummary,
    SeverityLiteral,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.applicability import (
    applies_to_roles,
    is_applicable,
    normalise_role,
)


@runtime_checkable
class ArticleCheck(Protocol):
    """Protocol that every article check must satisfy."""

    rule_id: str
    rule_name: str
    article: str
    severity: SeverityLiteral

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck: ...


def _na_check(check: ArticleCheck, role: str) -> ComplianceCheck:
    """Build a not-applicable ComplianceCheck for a given role."""
    roles = ", ".join(r for r in applies_to_roles(check.article) if r != "all")
    if role == "undeclared":
        description = "Not scored: no role declared."
        reasoning = (
            f"{check.article} applies only to these roles: {roles or 'n/a'}. "
            "No role was declared and a codebase cannot show whether it is "
            "deployed or is a general-purpose AI model, so this obligation is "
            "not scored. Re-run with a declared role to assess it."
        )
    else:
        description = f"Not applicable for declared role: {role}."
        reasoning = (
            f"{check.article} applies only to these roles: {roles or 'n/a'}. "
            f"Skipped for declared role '{role}' to avoid misleading findings."
        )
    return ComplianceCheck(
        rule_id=check.rule_id,
        rule_name=check.rule_name,
        article=check.article,
        status="N/A",
        severity="info",
        evidence=CheckEvidence(
            description=description,
            source="role_applicability",
        ),
        details={"applicable": False, "role": role},
        remediation=None,
        reasoning=reasoning,
        evidence_locations=[],
        sub_checks=[],
        is_applicable=False,
    )


class ComplianceEngine:
    """Runs all registered article checks and produces an AssessmentResult.

    Pure orchestration — no side effects. Iterates checks, collects results,
    computes summary statistics. Honours role-based applicability.
    """

    def __init__(self, checks: Sequence[ArticleCheck]) -> None:
        self._checks = list(checks)

    def run(
        self,
        scanner_output: ScannerOutput,
        role: str = "undeclared",
        sme: bool = False,
    ) -> AssessmentResult:
        """Execute all checks against scanner output and return full assessment.

        For each check:
        - if applicable to `role`, run the check normally
        - otherwise emit an N/A result that does not affect the score
        """
        norm_role = normalise_role(role)
        results: list[ComplianceCheck] = []
        for check in self._checks:
            if is_applicable(check.article, norm_role):
                results.append(check.evaluate(scanner_output))
            else:
                results.append(_na_check(check, norm_role))

        summary = self._compute_summary(results)
        return AssessmentResult(
            checks=results,
            summary=summary,
            role=norm_role,
            sme=bool(sme),
            role_declared=norm_role != "undeclared",
        )

    def run_advisory(
        self,
        scanner_output: ScannerOutput,
        role: str = "undeclared",
    ) -> list[ComplianceCheck]:
        """Run checks for informational purposes only (not scored).

        Honours role applicability so libraries/tools don't get advisory
        Art. 9–15 noise either.
        """
        norm_role = normalise_role(role)
        out: list[ComplianceCheck] = []
        for check in self._checks:
            if is_applicable(check.article, norm_role):
                out.append(check.evaluate(scanner_output))
            else:
                out.append(_na_check(check, norm_role))
        return out

    def _compute_summary(self, checks: list[ComplianceCheck]) -> ComplianceSummary:
        """Compute aggregate statistics from individual check results.

        N/A checks are excluded from totals, score, and critical_failures so
        out-of-scope articles never affect the headline numbers.
        """
        applicable = [c for c in checks if c.is_applicable]
        total = len(applicable)
        passed = sum(1 for c in applicable if c.status == "PASS")
        failed = sum(1 for c in applicable if c.status == "FAIL")
        partial = sum(1 for c in applicable if c.status == "PARTIAL")

        critical_failures = [
            c.rule_id for c in applicable
            if c.status == "FAIL" and c.severity == "critical"
        ]

        score = self._compute_score(applicable) if total > 0 else 0

        if total == 0:
            overall = "COMPLIANT"
        elif failed == 0 and partial == 0:
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
        Caller filters out N/A before invoking — defensive double-check below.
        """
        severity_weight: dict[str, float] = {
            "critical": 2.0,
            "high": 1.5,
            "medium": 1.0,
            "low": 0.5,
            "info": 0.0,  # safety net; N/A excluded by caller
        }
        status_score = {"PASS": 1.0, "PARTIAL": 0.5, "FAIL": 0.0, "N/A": 0.0}

        weighted = [
            (severity_weight.get(c.severity, 1.0), status_score.get(c.status, 0.0))
            for c in checks
            if c.status != "N/A"
        ]
        total_weight = sum(w for w, _ in weighted)
        earned = sum(w * s for w, s in weighted)

        return round((earned / total_weight) * 100) if total_weight > 0 else 0
