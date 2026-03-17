"""Article 11 — Technical Documentation compliance check.

EU AI Act Article 11 requires technical documentation to be drawn up before
the AI system is placed on the market or put into service.

Sub-checks:
1. model_card_exists — model card or equivalent documentation found
2. architecture_documented — system architecture is documented
3. performance_recorded — performance metrics are recorded
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput


class Article11Check:
    """Technical Documentation compliance check per EU AI Act Article 11."""

    rule_id: str = "EU_AI_ART_11"
    rule_name: str = "Technical Documentation"
    article: str = "Article 11"
    severity: SeverityLiteral = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        model_card = scanner_output.has_model_card
        architecture = scanner_output.has_architecture_docs
        performance = scanner_output.performance_metrics is not None

        sub_checks = {
            "model_card_exists": model_card,
            "architecture_documented": architecture,
            "performance_recorded": performance,
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

    def _describe(self, status: str) -> str:
        if status == "PASS":
            return (
                "Technical documentation complete: model card, architecture,"
                " and performance metrics present."
            )
        return "Technical documentation incomplete."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["model_card_exists"]:
            actions.append(
                "Create a model card documenting the AI system's purpose,"
                " design, and limitations."
            )
        if not sub_checks["architecture_documented"]:
            actions.append(
                "Document system architecture including model type,"
                " training approach, and data flow."
            )
        if not sub_checks["performance_recorded"]:
            actions.append(
                "Record performance metrics on test sets"
                " (accuracy, precision, recall, F1)."
            )
        return " ".join(actions)
