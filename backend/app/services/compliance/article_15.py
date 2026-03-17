"""Article 15 — Accuracy, Robustness, and Cybersecurity compliance check.

EU AI Act Article 15 requires high-risk AI systems to achieve an appropriate
level of accuracy, robustness, and cybersecurity.

Sub-checks:
1. test_metrics_logged — test set performance metrics are logged
2. adversarial_tested — adversarial robustness has been tested
3. versioning_in_place — model versioning exists for security/rollback
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import PerformanceMetrics, ScannerOutput


class Article15Check:
    """Accuracy, Robustness, and Cybersecurity check per EU AI Act Article 15."""

    rule_id: str = "EU_AI_ART_15"
    rule_name: str = "Accuracy, Robustness, Cybersecurity"
    article: str = "Article 15"
    severity: SeverityLiteral = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        metrics = scanner_output.performance_metrics or PerformanceMetrics()

        test_metrics = self._check_test_metrics(metrics)
        adversarial = metrics.adversarial_tested
        versioning = scanner_output.has_versioning

        sub_checks = {
            "test_metrics_logged": test_metrics,
            "adversarial_tested": adversarial,
            "versioning_in_place": versioning,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        status = "PASS" if passed == 3 else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._describe(status),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=sub_checks,
            remediation=remediation,
        )

    def _check_test_metrics(self, metrics: PerformanceMetrics) -> bool:
        """Test metrics logged if any standard metric has a value."""
        return any(
            v is not None
            for v in [
                metrics.accuracy,
                metrics.precision,
                metrics.recall,
                metrics.f1,
                metrics.auc,
            ]
        )

    def _describe(self, status: str) -> str:
        if status == "PASS":
            return "Accuracy, robustness, and cybersecurity requirements met."
        return "Gaps in accuracy testing, adversarial robustness, or versioning."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["test_metrics_logged"]:
            actions.append(
                "Log test set performance metrics"
                " (accuracy, precision, recall, F1)."
            )
        if not sub_checks["adversarial_tested"]:
            actions.append(
                "Conduct adversarial robustness testing and document results."
            )
        if not sub_checks["versioning_in_place"]:
            actions.append(
                "Implement model versioning for rollback capability"
                " and change tracking."
            )
        return " ".join(actions)
