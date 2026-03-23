"""Article 14 — Human Oversight compliance check.

EU AI Act Article 14 requires high-risk AI systems to be designed and developed
such that they can be effectively overseen by natural persons during use.

Sub-checks:
1. human_in_loop_documented — human-in-the-loop mechanism is documented
2. override_capability — humans can override AI decisions
3. escalation_procedures — procedures for escalation are documented
4. automation_bias_awareness — awareness of automation bias [Art. 14(4)(b)]
5. stop_mechanism — stop button or similar for safe halt [Art. 14(4)(e)]
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_14


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
        automation_bias = scanner_output.has_automation_bias_docs
        stop_mechanism = scanner_output.has_stop_mechanism

        sub_checks = {
            "human_in_loop_documented": human_docs,
            "override_capability": override,
            "escalation_procedures": escalation,
            "automation_bias_awareness": automation_bias,
            "stop_mechanism": stop_mechanism,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        total = len(sub_checks)
        status = "PASS" if passed == total else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._describe(status, sub_checks),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=sub_checks,
            remediation=remediation,
        )

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "human_in_loop_documented": f"no HITL documentation — {ART_14['human_in_loop']}",
        "override_capability": f"no override capability — {ART_14['override']}",
        "escalation_procedures": f"no escalation procedures — {ART_14['escalation']}",
        "automation_bias_awareness": f"no automation bias awareness — {ART_14['automation_bias']}",
        "stop_mechanism": f"no stop mechanism — {ART_14['stop_mechanism']}",
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Human oversight requirements met: HITL documented,"
                " override capability, escalation procedures,"
                " automation bias awareness, and stop mechanism in place."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Human oversight gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["human_in_loop_documented"]:
            actions.append(
                "Document human-in-the-loop mechanisms and review"
                " processes per Art. 14(1)."
            )
        if not sub_checks["override_capability"]:
            actions.append(
                "Implement and document human override capability"
                " for AI decisions per Art. 14(4)(d)."
            )
        if not sub_checks["escalation_procedures"]:
            actions.append(
                "Define escalation procedures for when human"
                " intervention is needed per Art. 14(4)(c)."
            )
        if not sub_checks["automation_bias_awareness"]:
            actions.append(
                "Document awareness of automation bias tendency"
                " per Art. 14(4)(b)."
            )
        if not sub_checks["stop_mechanism"]:
            actions.append(
                "Implement a stop button or similar procedure"
                " for safe halt per Art. 14(4)(e)."
            )
        return " ".join(actions)
