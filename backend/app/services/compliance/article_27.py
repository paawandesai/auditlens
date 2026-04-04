"""Article 27 — Fundamental Rights Impact Assessment.

EU AI Act Article 27 requires deployers of high-risk AI systems to conduct
a fundamental rights impact assessment before putting the system into use.
This assessment must describe processes, identify affected categories,
assess specific risks, and establish oversight and complaint mechanisms.

Sub-checks:
1. processes_described — has_user_instructions OR has_model_card
2. affected_categories_identified — detected_domains is non-empty
3. specific_risks_assessed — has_risk_assessment AND has_impact_assessment
4. oversight_mechanisms — has_human_oversight_docs
5. complaint_mechanisms — has_escalation_docs
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_27


class Article27Check:
    """Fundamental Rights Impact Assessment per EU AI Act Article 27."""

    rule_id: str = "EU_AI_ART_27"
    rule_name: str = "Fundamental Rights Impact Assessment"
    article: str = "Article 27"
    severity: SeverityLiteral = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        processes_described = (
            scanner_output.has_user_instructions or scanner_output.has_model_card
        )
        affected_categories = bool(scanner_output.detected_domains)
        specific_risks = (
            scanner_output.has_risk_assessment and scanner_output.has_impact_assessment
        )
        oversight = scanner_output.has_human_oversight_docs
        complaint = scanner_output.has_escalation_docs

        sub_checks_raw: dict[str, bool] = {
            "processes_described": processes_described,
            "affected_categories_identified": affected_categories,
            "specific_risks_assessed": specific_risks,
            "oversight_mechanisms": oversight,
            "complaint_mechanisms": complaint,
        }

        sub_check_meta: dict[str, tuple[str, list[str], str]] = {
            "processes_described": (
                "Deployer processes using the AI system are described",
                ["USAGE*", "user_guide*", "MODEL_CARD*", "model_card*"],
                ART_27["deployer_processes"],
            ),
            "affected_categories_identified": (
                "Categories of affected natural persons and groups identified",
                ["docs/impact*", "IMPACT_ASSESSMENT*"],
                ART_27["affected_categories"],
            ),
            "specific_risks_assessed": (
                "Specific risks of harm to identified categories assessed",
                ["RISK_ASSESSMENT.md", "risk_assessment/*", "IMPACT_ASSESSMENT*"],
                ART_27["specific_risks"],
            ),
            "oversight_mechanisms": (
                "Human oversight measures documented",
                ["docs/human_oversight*", "HUMAN_REVIEW*", "docs/oversight*"],
                ART_27["oversight_complaint"],
            ),
            "complaint_mechanisms": (
                "Complaint and redress mechanisms established",
                ["docs/escalation*", "ESCALATION*", "docs/complaint*"],
                ART_27["oversight_complaint"],
            ),
        }

        # Map sub-check IDs to scanner field names for matched_paths lookup.
        scanner_field_map: dict[str, list[str]] = {
            "processes_described": ["has_user_instructions", "has_model_card"],
            "affected_categories_identified": ["has_impact_assessment"],
            "specific_risks_assessed": ["has_risk_assessment", "has_impact_assessment"],
            "oversight_mechanisms": ["has_human_oversight_docs"],
            "complaint_mechanisms": ["has_escalation_docs"],
        }

        sub_checks: list[SubCheckDetail] = []
        evidence_locations: list[str] = []

        for check_id, passed in sub_checks_raw.items():
            description, default_locations, article_ref = sub_check_meta[check_id]
            scanner_fields = scanner_field_map[check_id]
            actual_paths: list[str] = []
            for sf in scanner_fields:
                actual_paths.extend(scanner_output.matched_paths.get(sf, []))

            if check_id == "affected_categories_identified":
                if passed:
                    domains = [d.domain for d in scanner_output.detected_domains]
                    reasoning = (
                        f"Detected domains: {', '.join(domains)}."
                        " Affected categories can be inferred from domain analysis."
                    )
                else:
                    reasoning = (
                        "No domains detected in repository content."
                        " Cannot identify affected categories of natural persons."
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
            "Article 27 mandates a fundamental rights impact assessment (FRIA)"
            " before deploying a high-risk AI system. The FRIA must describe"
            " how the system will be used, identify who may be affected, assess"
            " specific risks to those groups, and establish oversight and"
            f" complaint mechanisms. {passed_count}/{total} FRIA components evidenced."
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
        "processes_described": f"no process description — {ART_27['deployer_processes']}",
        "affected_categories_identified": f"no affected categories — {ART_27['affected_categories']}",
        "specific_risks_assessed": f"no specific risk assessment — {ART_27['specific_risks']}",
        "oversight_mechanisms": f"no oversight mechanisms — {ART_27['oversight_complaint']}",
        "complaint_mechanisms": f"no complaint mechanisms — {ART_27['oversight_complaint']}",
    }

    def _describe(self, status: str, sub_checks: dict[str, bool]) -> str:
        if status == "PASS":
            return (
                "Fundamental rights impact assessment documented with process"
                " description, affected categories, risk assessment, oversight"
                " mechanisms, and complaint procedures."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"FRIA gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict[str, bool]) -> str:
        actions: list[str] = []
        if not sub_checks["processes_described"]:
            actions.append(
                "Describe the deployer's processes that use the AI system"
                " per Art. 27(1)(a)."
            )
        if not sub_checks["affected_categories_identified"]:
            actions.append(
                "Identify categories of natural persons and groups likely"
                " to be affected per Art. 27(1)(c)."
            )
        if not sub_checks["specific_risks_assessed"]:
            actions.append(
                "Conduct a specific risk assessment for identified affected"
                " categories per Art. 27(1)(d). Create both a risk assessment"
                " and an impact assessment document."
            )
        if not sub_checks["oversight_mechanisms"]:
            actions.append(
                "Document human oversight measures per Art. 27(1)(f)."
            )
        if not sub_checks["complaint_mechanisms"]:
            actions.append(
                "Establish complaint and redress mechanisms for affected"
                " persons per Art. 27(1)(f)."
            )
        return " ".join(actions)
