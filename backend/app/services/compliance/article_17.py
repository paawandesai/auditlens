"""Article 17 — Quality Management System.

EU AI Act Article 17 requires providers of high-risk AI systems to put in
place a quality management system that ensures compliance throughout the
lifecycle. The QMS must cover strategy, design, testing, risk management,
and incident reporting procedures.

Sub-checks:
1. compliance_strategy — has_qms_docs OR has_conformity_assessment
2. design_development — has_development_process_docs OR has_architecture_docs
3. testing_validation — has_test_suite
4. risk_management — has_risk_assessment
5. incident_reporting — has_incident_reporting
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_17


class Article17Check:
    """Quality Management System compliance check per EU AI Act Article 17."""

    rule_id: str = "EU_AI_ART_17"
    rule_name: str = "Quality Management System"
    article: str = "Article 17"
    severity: SeverityLiteral = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        compliance_strategy = (
            scanner_output.has_qms_docs or scanner_output.has_conformity_assessment
        )
        design_development = (
            scanner_output.has_development_process_docs
            or scanner_output.has_architecture_docs
        )
        testing_validation = scanner_output.has_test_suite
        risk_management = scanner_output.has_risk_assessment
        incident_reporting = scanner_output.has_incident_reporting

        sub_checks_raw: dict[str, bool] = {
            "compliance_strategy": compliance_strategy,
            "design_development": design_development,
            "testing_validation": testing_validation,
            "risk_management": risk_management,
            "incident_reporting": incident_reporting,
        }

        sub_check_meta: dict[str, tuple[str, list[str], str]] = {
            "compliance_strategy": (
                "Regulatory compliance strategy documented",
                ["docs/qms*", "QUALITY*", "docs/conformity*", "CONFORMITY*"],
                ART_17["compliance_strategy"],
            ),
            "design_development": (
                "Design and development procedures documented",
                ["ARCHITECTURE*", "docs/design*", "docs/development*"],
                ART_17["design_procedures"],
            ),
            "testing_validation": (
                "Testing and validation procedures in place",
                ["tests/", "test/", "spec/"],
                ART_17["testing_procedures"],
            ),
            "risk_management": (
                "Risk management procedures documented",
                ["RISK_ASSESSMENT.md", "risk_assessment/*", "docs/risk*"],
                ART_17["risk_procedures"],
            ),
            "incident_reporting": (
                "Incident reporting procedures established per Art. 73",
                ["docs/incident*", "INCIDENT*", ".github/ISSUE_TEMPLATE/*"],
                ART_17["incident_reporting"],
            ),
        }

        # Map sub-check IDs to scanner field names for matched_paths lookup.
        scanner_field_map: dict[str, list[str]] = {
            "compliance_strategy": ["has_qms_docs", "has_conformity_assessment"],
            "design_development": ["has_development_process_docs", "has_architecture_docs"],
            "testing_validation": ["has_test_suite"],
            "risk_management": ["has_risk_assessment"],
            "incident_reporting": ["has_incident_reporting"],
        }

        sub_checks: list[SubCheckDetail] = []
        evidence_locations: list[str] = []

        for check_id, passed in sub_checks_raw.items():
            description, default_locations, article_ref = sub_check_meta[check_id]
            scanner_fields = scanner_field_map[check_id]
            actual_paths: list[str] = []
            for sf in scanner_fields:
                actual_paths.extend(scanner_output.matched_paths.get(sf, []))
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
            "Article 17 requires a quality management system (QMS) that covers"
            " the entire AI system lifecycle. A QMS ensures systematic compliance"
            " with regulatory requirements through documented strategies, design"
            " procedures, testing protocols, risk management, and incident"
            f" reporting. {passed_count}/{total} QMS components evidenced."
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
        "compliance_strategy": f"no compliance strategy — {ART_17['compliance_strategy']}",
        "design_development": f"no design/development procedures — {ART_17['design_procedures']}",
        "testing_validation": f"no testing/validation procedures — {ART_17['testing_procedures']}",
        "risk_management": f"no risk management procedures — {ART_17['risk_procedures']}",
        "incident_reporting": f"no incident reporting — {ART_17['incident_reporting']}",
    }

    def _describe(self, status: str, sub_checks: dict[str, bool]) -> str:
        if status == "PASS":
            return (
                "Quality management system documented with compliance strategy,"
                " design procedures, testing protocols, risk management,"
                " and incident reporting."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"QMS gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict[str, bool]) -> str:
        actions: list[str] = []
        if not sub_checks["compliance_strategy"]:
            actions.append(
                "Document a regulatory compliance strategy covering"
                " Art. 8-15 requirements per Art. 17(1)(a)."
            )
        if not sub_checks["design_development"]:
            actions.append(
                "Document design and development procedures, techniques,"
                " and system specifications per Art. 17(1)(b)."
            )
        if not sub_checks["testing_validation"]:
            actions.append(
                "Establish testing and validation procedures"
                " per Art. 17(1)(c)."
            )
        if not sub_checks["risk_management"]:
            actions.append(
                "Document risk management procedures"
                " per Art. 17(1)(e)."
            )
        if not sub_checks["incident_reporting"]:
            actions.append(
                "Establish incident reporting procedures for serious"
                " incidents per Art. 17(1)(g) / Art. 73."
            )
        return " ".join(actions)
