"""Article 9 — Risk Management System compliance check.

EU AI Act Article 9 requires a risk management system that identifies and
analyses known and reasonably foreseeable risks, estimates and evaluates
risks, and adopts suitable risk management measures.

Sub-checks:
1. risk_assessment_exists — risk assessment documentation found
2. failure_modes_cataloged — failure modes identified and documented
3. mitigation_documented — risk mitigation measures documented
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput


class Article09Check:
    """Risk Management System compliance check per EU AI Act Article 9."""

    rule_id: str = "EU_AI_ART_9"
    rule_name: str = "Risk Management System"
    article: str = "Article 9"
    severity: SeverityLiteral = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        risk_assessment = scanner_output.has_risk_assessment
        failure_modes = scanner_output.has_failure_modes_doc
        mitigation = scanner_output.has_mitigation_plan

        sub_checks = {
            "risk_assessment_exists": risk_assessment,
            "failure_modes_cataloged": failure_modes,
            "mitigation_documented": mitigation,
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
                description=self._describe(status, sub_checks),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=sub_checks,
            remediation=remediation,
        )

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "risk_assessment_exists": "no risk assessment found",
        "failure_modes_cataloged": "no failure modes documentation",
        "mitigation_documented": "no mitigation plan",
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return "Risk management system documented with failure modes and mitigation measures."
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Risk management gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["risk_assessment_exists"]:
            actions.append("Create a risk assessment documenting known and foreseeable risks.")
        if not sub_checks["failure_modes_cataloged"]:
            actions.append("Catalog failure modes and their potential impacts.")
        if not sub_checks["mitigation_documented"]:
            actions.append("Document risk mitigation measures and residual risk acceptance.")
        return " ".join(actions)
