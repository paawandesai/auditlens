"""Article 16 — Obligations of Providers of High-Risk AI Systems.

EU AI Act Article 16 sets out the obligations that providers of high-risk AI
systems must fulfil, including ensuring compliance with Art. 8-15, designating
a contact person, establishing a quality management system, conducting
conformity assessment, and implementing post-market monitoring.

Sub-checks:
1. system_compliance — aggregate of has_risk_assessment AND has_model_card AND has_test_suite
2. contact_person_designated — has_contact_info
3. qms_in_place — has_qms_docs
4. conformity_assessment_done — has_conformity_assessment
5. post_market_monitoring — has_monitoring_config
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_16


class Article16Check:
    """Provider Obligations compliance check per EU AI Act Article 16."""

    rule_id: str = "EU_AI_ART_16"
    rule_name: str = "Provider Obligations"
    article: str = "Article 16"
    severity: SeverityLiteral = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        system_compliance = (
            scanner_output.has_risk_assessment
            and scanner_output.has_model_card
            and scanner_output.has_test_suite
        )
        contact_person = scanner_output.has_contact_info
        qms = scanner_output.has_qms_docs
        conformity = scanner_output.has_conformity_assessment
        post_market = scanner_output.has_monitoring_config

        sub_checks_raw: dict[str, bool] = {
            "system_compliance": system_compliance,
            "contact_person_designated": contact_person,
            "qms_in_place": qms,
            "conformity_assessment_done": conformity,
            "post_market_monitoring": post_market,
        }

        sub_check_meta: dict[str, tuple[str, list[str], str]] = {
            "system_compliance": (
                "Core Art. 8-15 compliance: risk assessment, model card, and test suite present",
                ["RISK_ASSESSMENT.md", "MODEL_CARD*", "tests/"],
                ART_16["system_compliance"],
            ),
            "contact_person_designated": (
                "Contact person designated and reachable by competent authority",
                ["SECURITY.md", "CONTRIBUTING.md", "SUPPORT.md", "MAINTAINERS*"],
                ART_16["contact_person"],
            ),
            "qms_in_place": (
                "Quality management system documented per Art. 17",
                ["docs/qms*", "QUALITY*", "quality_management*"],
                ART_16["qms"],
            ),
            "conformity_assessment_done": (
                "Conformity assessment procedure completed per Art. 43",
                ["docs/conformity*", "CONFORMITY*", "conformity_assessment*"],
                ART_16["conformity"],
            ),
            "post_market_monitoring": (
                "Post-market monitoring system established per Art. 72",
                ["docs/monitoring*", "monitoring.yaml", ".github/workflows/*"],
                ART_16["post_market"],
            ),
        }

        # Map sub-check IDs to scanner field names for matched_paths lookup.
        scanner_field_map: dict[str, list[str]] = {
            "system_compliance": ["has_risk_assessment", "has_model_card", "has_test_suite"],
            "contact_person_designated": ["has_contact_info"],
            "qms_in_place": ["has_qms_docs"],
            "conformity_assessment_done": ["has_conformity_assessment"],
            "post_market_monitoring": ["has_monitoring_config"],
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
            "Article 16 enumerates the obligations of providers of high-risk AI"
            " systems. Providers must ensure the system complies with Art. 8-15,"
            " designate a contact person, maintain a QMS, complete conformity"
            f" assessment, and implement post-market monitoring. {passed_count}/{total}"
            " obligations evidenced."
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
        "system_compliance": f"core Art. 8-15 compliance not met — {ART_16['system_compliance']}",
        "contact_person_designated": f"no contact person designated — {ART_16['contact_person']}",
        "qms_in_place": f"no quality management system — {ART_16['qms']}",
        "conformity_assessment_done": f"no conformity assessment — {ART_16['conformity']}",
        "post_market_monitoring": f"no post-market monitoring — {ART_16['post_market']}",
    }

    def _describe(self, status: str, sub_checks: dict[str, bool]) -> str:
        if status == "PASS":
            return (
                "Provider obligations satisfied: system complies with Art. 8-15,"
                " contact person designated, QMS in place, conformity assessment"
                " done, post-market monitoring established."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Provider obligation gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict[str, bool]) -> str:
        actions: list[str] = []
        if not sub_checks["system_compliance"]:
            actions.append(
                "Ensure the AI system complies with Art. 8-15 requirements"
                " (risk assessment, model card, test suite) per Art. 16(a)."
            )
        if not sub_checks["contact_person_designated"]:
            actions.append(
                "Designate a contact person reachable by competent authorities"
                " per Art. 16(j). Add contact info to SECURITY.md or CONTRIBUTING.md."
            )
        if not sub_checks["qms_in_place"]:
            actions.append(
                "Establish a quality management system per Art. 16(c) / Art. 17."
            )
        if not sub_checks["conformity_assessment_done"]:
            actions.append(
                "Complete the conformity assessment procedure per Art. 16(f) / Art. 43."
            )
        if not sub_checks["post_market_monitoring"]:
            actions.append(
                "Implement a post-market monitoring system per Art. 16(h) / Art. 72."
            )
        return " ".join(actions)
