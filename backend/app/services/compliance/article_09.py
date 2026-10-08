"""Article 9 — Risk Management System compliance check.

EU AI Act Article 9 requires a risk management system that identifies and
analyses known and reasonably foreseeable risks, estimates and evaluates
risks, and adopts suitable risk management measures.

Sub-checks:
1. risk_assessment_exists — risk assessment documentation found
2. failure_modes_cataloged — failure modes identified and documented
3. mitigation_documented — risk mitigation measures documented
4. residual_risk_evaluated — residual risk judged acceptable [Art. 9(5)]
5. testing_against_metrics — tested against prior-defined metrics [Art. 9(6)]
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral, SubCheckDetail
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_9


class Article09Check:
    """Risk Management System compliance check per EU AI Act Article 9."""

    rule_id: str = "EU_AI_ART_9"
    rule_name: str = "Risk Management System"
    article: str = "Article 9"
    severity: SeverityLiteral = "critical"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "risk_assessment_exists": (
            "Risk assessment documentation present in repository",
            ["RISK_ASSESSMENT.md", "risk_assessment/*", "docs/risk*"],
            ART_9["risk_assessment"],
        ),
        "failure_modes_cataloged": (
            "Failure modes identified and documented",
            ["tests/risk/*", "tests/safety/*"],
            ART_9["failure_modes"],
        ),
        "mitigation_documented": (
            "Risk mitigation measures documented",
            ["docs/monitoring*", "docs/risk*"],
            ART_9["mitigation"],
        ),
        "residual_risk_evaluated": (
            "Residual risk evaluated and judged acceptable",
            ["docs/risk/*", "RISK_ASSESSMENT.md"],
            ART_9["residual_risk"],
        ),
        "testing_against_metrics": (
            "Testing against prior-defined metrics documented",
            ["docs/testing/*", "tests/acceptance/*"],
            ART_9["testing_metrics"],
        ),
    }

    # Map sub-check IDs to scanner field names for matched_paths lookup.
    _SCANNER_FIELD_MAP: dict[str, str] = {
        "risk_assessment_exists": "has_risk_assessment",
        "failure_modes_cataloged": "has_failure_modes_doc",
        "mitigation_documented": "has_mitigation_plan",
        "residual_risk_evaluated": "has_residual_risk_evaluation",
        "testing_against_metrics": "has_testing_metrics_defined",
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        # Demote any flag whose only matching files are placeholders.
        # Empty `RISK_ASSESSMENT.md` should not pass Art. 9(2)(a).
        placeholders = set(scanner_output.placeholder_paths)

        def _real(field: str) -> bool:
            if not getattr(scanner_output, field, False):
                return False
            paths = scanner_output.matched_paths.get(field, [])
            if not paths:
                return True  # detection came from content flags, not file paths
            return any(p not in placeholders for p in paths)

        risk_assessment = _real("has_risk_assessment")
        failure_modes = _real("has_failure_modes_doc")
        mitigation = _real("has_mitigation_plan")
        residual_risk = _real("has_residual_risk_evaluation")
        testing_metrics = _real("has_testing_metrics_defined")

        sub_checks = {
            "risk_assessment_exists": risk_assessment,
            "failure_modes_cataloged": failure_modes,
            "mitigation_documented": mitigation,
            "residual_risk_evaluated": residual_risk,
            "testing_against_metrics": testing_metrics,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        total = len(sub_checks)
        status = "PASS" if passed == total else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

        rich_sub_checks: list[SubCheckDetail] = []
        for check_id, value in sub_checks.items():
            description, default_locations, article_ref = self._SUB_CHECK_META[check_id]
            scanner_field = self._SCANNER_FIELD_MAP[check_id]
            actual_paths = scanner_output.matched_paths.get(scanner_field, [])
            reasoning = (
                f"Found: {', '.join(actual_paths)}"
                if value and actual_paths
                else f"Evidence detected via content analysis — {description.lower()}"
                if value
                else f"No evidence for {check_id.replace('_', ' ')} found. Expected files: {', '.join(default_locations)}."
            )
            rich_sub_checks.append(SubCheckDetail(
                id=check_id,
                description=description,
                passed=value,
                reasoning=reasoning,
                locations=actual_paths if value and actual_paths else default_locations,
                article_reference=article_ref,
            ))

        evidence_locations = [
            path
            for sc in rich_sub_checks
            if sc.passed
            for path in sc.locations
        ]

        overall_reasoning = (
            "Article 9 requires a risk management system throughout the AI system"
            f" lifecycle. This repository shows {passed} of {total} risk management"
            " signals, indicating "
            + ("full" if passed == total else "partial" if passed > 0 else "no")
            + " risk management documentation."
        )

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
            reasoning=overall_reasoning,
            evidence_locations=evidence_locations,
            sub_checks=rich_sub_checks,
        )

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "risk_assessment_exists": f"no risk assessment found — {ART_9['risk_assessment']}",
        "failure_modes_cataloged": f"no failure modes documentation — {ART_9['failure_modes']}",
        "mitigation_documented": f"no mitigation plan — {ART_9['mitigation']}",
        "residual_risk_evaluated": f"no residual risk evaluation — {ART_9['residual_risk']}",
        "testing_against_metrics": f"no testing against defined metrics — {ART_9['testing_metrics']}",
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Risk management system documented with failure modes,"
                " mitigation measures, residual risk evaluation, and testing metrics."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Risk management gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["risk_assessment_exists"]:
            actions.append(
                "Create a risk assessment documenting known and foreseeable risks"
                " per Art. 9(2)(a)."
            )
        if not sub_checks["failure_modes_cataloged"]:
            actions.append(
                "Catalog failure modes and their potential impacts"
                " under foreseeable misuse per Art. 9(2)(b)."
            )
        if not sub_checks["mitigation_documented"]:
            actions.append(
                "Document risk mitigation measures per Art. 9(2)(d)."
            )
        if not sub_checks["residual_risk_evaluated"]:
            actions.append(
                "Evaluate and document residual risks after mitigation"
                " per Art. 9(5)."
            )
        if not sub_checks["testing_against_metrics"]:
            actions.append(
                "Define acceptance criteria and test against prior-defined"
                " metrics per Art. 9(6)."
            )
        return " ".join(actions)
