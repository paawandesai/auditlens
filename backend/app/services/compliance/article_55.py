"""Article 55 — Obligations for Providers of GPAI Models with Systemic Risk.

EU AI Act Article 55 imposes additional obligations on providers of
general-purpose AI models that pose systemic risk. These include model
evaluation with adversarial testing, systemic risk assessment and mitigation,
incident tracking and reporting, and cybersecurity protection.

Sub-checks:
1. model_evaluation — has_test_suite AND performance_metrics is not None
2. systemic_risk_assessment — has_risk_assessment AND has_impact_assessment
3. incident_tracking — has_incident_reporting AND has_risk_event_logging
4. cybersecurity_protection — has_cybersecurity_docs
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_55


class Article55Check:
    """Systemic Risk GPAI Obligations per EU AI Act Article 55."""

    rule_id: str = "EU_AI_ART_55"
    rule_name: str = "Systemic Risk GPAI Obligations"
    article: str = "Article 55"
    severity: SeverityLiteral = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        model_evaluation = (
            scanner_output.has_test_suite
            and scanner_output.performance_metrics is not None
        )
        systemic_risk = (
            scanner_output.has_risk_assessment and scanner_output.has_impact_assessment
        )
        incident_tracking = (
            scanner_output.has_incident_reporting
            and scanner_output.has_risk_event_logging
        )
        cybersecurity = scanner_output.has_cybersecurity_docs

        sub_checks_raw: dict[str, bool] = {
            "model_evaluation": model_evaluation,
            "systemic_risk_assessment": systemic_risk,
            "incident_tracking": incident_tracking,
            "cybersecurity_protection": cybersecurity,
        }

        sub_check_meta: dict[str, tuple[str, list[str], str]] = {
            "model_evaluation": (
                "Model evaluation performed including adversarial testing",
                ["tests/", "eval_results*", "benchmark*", "metrics*"],
                ART_55["model_evaluation"],
            ),
            "systemic_risk_assessment": (
                "Systemic risks assessed and mitigated",
                ["RISK_ASSESSMENT.md", "risk_assessment/*", "IMPACT_ASSESSMENT*"],
                ART_55["systemic_risk"],
            ),
            "incident_tracking": (
                "Serious incidents tracked, documented, and reported",
                ["docs/incident*", "INCIDENT*", ".github/ISSUE_TEMPLATE/*"],
                ART_55["incident_tracking"],
            ),
            "cybersecurity_protection": (
                "Adequate level of cybersecurity protection ensured",
                ["SECURITY.md", "docs/security*", "docs/cybersecurity*"],
                ART_55["cybersecurity"],
            ),
        }

        # Map sub-check IDs to scanner field names for matched_paths lookup.
        scanner_field_map: dict[str, list[str]] = {
            "model_evaluation": ["has_test_suite", "has_performance_metrics"],
            "systemic_risk_assessment": ["has_risk_assessment", "has_impact_assessment"],
            "incident_tracking": ["has_incident_reporting", "has_risk_event_logging"],
            "cybersecurity_protection": ["has_cybersecurity_docs"],
        }

        sub_checks: list[SubCheckDetail] = []
        evidence_locations: list[str] = []

        for check_id, passed in sub_checks_raw.items():
            description, default_locations, article_ref = sub_check_meta[check_id]
            scanner_fields = scanner_field_map[check_id]
            actual_paths: list[str] = []
            for sf in scanner_fields:
                actual_paths.extend(scanner_output.matched_paths.get(sf, []))

            if check_id == "model_evaluation":
                if passed:
                    reasoning = (
                        f"Found: {', '.join(actual_paths)}"
                        if actual_paths
                        else "Test suite found and performance metrics are present."
                        " Model evaluation evidence detected."
                    )
                else:
                    missing = []
                    if not scanner_output.has_test_suite:
                        missing.append("test suite")
                    if scanner_output.performance_metrics is None:
                        missing.append("performance metrics")
                    reasoning = (
                        f"Missing: {', '.join(missing)}."
                        f" Expected files: {', '.join(default_locations)}."
                    )
            elif check_id == "incident_tracking":
                if passed:
                    reasoning = (
                        f"Found: {', '.join(actual_paths)}"
                        if actual_paths
                        else "Incident reporting and risk event logging both detected."
                    )
                else:
                    missing = []
                    if not scanner_output.has_incident_reporting:
                        missing.append("incident reporting")
                    if not scanner_output.has_risk_event_logging:
                        missing.append("risk event logging")
                    reasoning = (
                        f"Missing: {', '.join(missing)}."
                        f" Expected files: {', '.join(default_locations)}."
                    )
            else:
                reasoning = (
                    f"Found: {', '.join(actual_paths)}"
                    if passed and actual_paths
                    else f"Evidence detected via content analysis — {description.lower()}"
                    if passed
                    else f"No evidence for {check_id.replace('_', ' ')} — "
                         f"expected files: {', '.join(default_locations)}."
                )

            sub_checks.append(SubCheckDetail(
                id=check_id,
                description=description,
                passed=passed,
                reasoning=reasoning,
                locations=actual_paths if passed and actual_paths else default_locations,
                article_reference=article_ref,
            ))
            if passed:
                evidence_locations.extend(actual_paths if actual_paths else default_locations)

        passed_count = sum(1 for v in sub_checks_raw.values() if v)
        total = len(sub_checks_raw)
        status = "PASS" if passed_count == total else ("FAIL" if passed_count == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks_raw) if status != "PASS" else None

        overall_reasoning = (
            "Article 55 applies to GPAI models classified as posing systemic"
            " risk — generally models trained with more than 10^25 FLOPs or"
            " designated by the AI Office. These providers face heightened"
            " obligations: adversarial model evaluation, systemic risk assessment,"
            f" incident tracking, and cybersecurity measures. {passed_count}/{total}"
            " systemic risk obligations evidenced."
        )

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._describe(status, sub_checks_raw),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=sub_checks_raw,
            remediation=remediation,
            reasoning=overall_reasoning,
            evidence_locations=evidence_locations,
            sub_checks=sub_checks,
        )

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "model_evaluation": f"no model evaluation — {ART_55['model_evaluation']}",
        "systemic_risk_assessment": f"no systemic risk assessment — {ART_55['systemic_risk']}",
        "incident_tracking": f"no incident tracking — {ART_55['incident_tracking']}",
        "cybersecurity_protection": f"no cybersecurity docs — {ART_55['cybersecurity']}",
    }

    def _describe(self, status: str, sub_checks: dict[str, bool]) -> str:
        if status == "PASS":
            return (
                "Systemic risk GPAI obligations satisfied: model evaluation"
                " performed, systemic risks assessed, incidents tracked,"
                " cybersecurity protection in place."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Systemic risk GPAI gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict[str, bool]) -> str:
        actions: list[str] = []
        if not sub_checks["model_evaluation"]:
            actions.append(
                "Perform model evaluation including adversarial testing and"
                " document performance metrics per Art. 55(1)(a)."
            )
        if not sub_checks["systemic_risk_assessment"]:
            actions.append(
                "Assess and mitigate systemic risks, including conducting"
                " an impact assessment per Art. 55(1)(b)."
            )
        if not sub_checks["incident_tracking"]:
            actions.append(
                "Establish incident tracking, documentation, and reporting"
                " procedures for serious incidents per Art. 55(1)(c)."
            )
        if not sub_checks["cybersecurity_protection"]:
            actions.append(
                "Document cybersecurity protection measures ensuring adequate"
                " security per Art. 55(1)(d)."
            )
        return " ".join(actions)
