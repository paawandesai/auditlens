"""Article 14 — Human Oversight compliance check.

EU AI Act Article 14 requires high-risk AI systems to be designed and developed
such that they can be effectively overseen by natural persons during use.

Sub-checks:
1. human_in_loop_documented — human-in-the-loop mechanism is documented
2. override_capability — humans can override AI decisions
3. escalation_procedures — procedures for escalation are documented
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput


class Article14Check:
    """Human Oversight compliance check per EU AI Act Article 14."""

    rule_id: str = "EU_AI_ART_14"
    rule_name: str = "Human Oversight"
    article: str = "Article 14"
    severity: SeverityLiteral = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        human_docs = scanner_output.has_human_oversight_docs
        override = scanner_output.has_override_mechanism
        escalation = scanner_output.has_escalation_docs

        sub_checks = {
            "human_in_loop_documented": human_docs,
            "override_capability": override,
            "escalation_procedures": escalation,
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
                "Human oversight requirements met: HITL documented,"
                " override capability, and escalation procedures in place."
            )
        return "Human oversight mechanisms incomplete or missing."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["human_in_loop_documented"]:
            actions.append("Document human-in-the-loop mechanisms and review processes.")
        if not sub_checks["override_capability"]:
            actions.append("Implement and document human override capability for AI decisions.")
        if not sub_checks["escalation_procedures"]:
            actions.append("Define escalation procedures for when human intervention is needed.")
        return " ".join(actions)
