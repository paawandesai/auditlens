"""Article 12 — Record-Keeping compliance check.

EU AI Act Article 12 requires automatic recording of events (logs) while
the high-risk AI system is operating.

Sub-checks:
1. logging_configured — logging/monitoring infrastructure exists
2. model_versioned — model versioning is in place
3. audit_trail_exists — audit trail for decisions exists
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput


class Article12Check:
    """Record-Keeping compliance check per EU AI Act Article 12."""

    rule_id: str = "EU_AI_ART_12"
    rule_name: str = "Record-Keeping"
    article: str = "Article 12"
    severity: SeverityLiteral = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        logging = scanner_output.has_logging_config
        versioning = scanner_output.has_versioning
        audit_trail = logging and versioning  # audit trail requires both

        sub_checks = {
            "logging_configured": logging,
            "model_versioned": versioning,
            "audit_trail_exists": audit_trail,
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
            return "Record-keeping requirements met: logging, versioning, and audit trail in place."
        return "Record-keeping gaps detected."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["logging_configured"]:
            actions.append("Configure logging infrastructure to record AI system events.")
        if not sub_checks["model_versioned"]:
            actions.append("Implement model versioning to track changes over time.")
        if not sub_checks["audit_trail_exists"]:
            actions.append("Establish an audit trail linking inputs, outputs, and model versions.")
        return " ".join(actions)
