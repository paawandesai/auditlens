"""Article 26 — Obligations of Deployers of High-Risk AI Systems.

EU AI Act Article 26 sets out obligations for deployers (users of AI systems
in a professional capacity). Deployers must use the system according to
instructions, assign human oversight, monitor operation, and inform affected
persons about AI system usage.

Sub-checks:
1. use_per_instructions — has_user_instructions
2. human_oversight_assigned — has_human_oversight_docs
3. operation_monitoring — has_monitoring_config OR has_logging_config
4. persons_informed — has_ai_disclosure
5. workplace_notification — has_ai_disclosure
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_26


class Article26Check:
    """Deployer Obligations compliance check per EU AI Act Article 26."""

    rule_id: str = "EU_AI_ART_26"
    rule_name: str = "Deployer Obligations"
    article: str = "Article 26"
    severity: SeverityLiteral = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        use_per_instructions = scanner_output.has_user_instructions
        human_oversight = scanner_output.has_human_oversight_docs
        operation_monitoring = (
            scanner_output.has_monitoring_config or scanner_output.has_logging_config
        )
        persons_informed = scanner_output.has_ai_disclosure
        workplace_notification = scanner_output.has_ai_disclosure

        sub_checks_raw: dict[str, bool] = {
            "use_per_instructions": use_per_instructions,
            "human_oversight_assigned": human_oversight,
            "operation_monitoring": operation_monitoring,
            "persons_informed": persons_informed,
            "workplace_notification": workplace_notification,
        }

        sub_check_meta: dict[str, tuple[str, list[str], str]] = {
            "use_per_instructions": (
                "AI system used in accordance with provider instructions",
                ["USAGE*", "user_guide*", "deployer_guide*", "docs/usage*"],
                ART_26["use_per_instructions"],
            ),
            "human_oversight_assigned": (
                "Human oversight assigned to competent natural persons",
                ["docs/human_oversight*", "HUMAN_REVIEW*", "docs/oversight*"],
                ART_26["human_oversight"],
            ),
            "operation_monitoring": (
                "Operational monitoring of the AI system in place",
                ["docs/monitoring*", "monitoring.yaml", "logging.conf", "logging.yaml"],
                ART_26["monitoring"],
            ),
            "persons_informed": (
                "Affected natural persons informed about AI system use",
                ["docs/ai_disclosure*", "AI_DISCLOSURE*", "TRANSPARENCY*"],
                ART_26["inform_affected"],
            ),
            "workplace_notification": (
                "Workers and their representatives informed about AI use",
                ["docs/ai_disclosure*", "AI_DISCLOSURE*", "TRANSPARENCY*"],
                ART_26["workplace_notification"],
            ),
        }

        # Map sub-check IDs to scanner field names for matched_paths lookup.
        scanner_field_map: dict[str, list[str]] = {
            "use_per_instructions": ["has_user_instructions"],
            "human_oversight_assigned": ["has_human_oversight_docs"],
            "operation_monitoring": ["has_monitoring_config", "has_logging_config"],
            "persons_informed": ["has_ai_disclosure"],
            "workplace_notification": ["has_ai_disclosure"],
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
            "Article 26 addresses deployer obligations — distinct from provider"
            " obligations (Art. 16). Deployers are organisations that use high-risk"
            " AI systems in a professional capacity. They must follow provider"
            " instructions, assign human oversight, monitor operations, and inform"
            f" affected persons. {passed_count}/{total} deployer obligations evidenced."
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
        "use_per_instructions": f"no usage instructions — {ART_26['use_per_instructions']}",
        "human_oversight_assigned": f"no human oversight docs — {ART_26['human_oversight']}",
        "operation_monitoring": f"no monitoring/logging — {ART_26['monitoring']}",
        "persons_informed": f"no AI disclosure — {ART_26['inform_affected']}",
        "workplace_notification": f"no workplace notification — {ART_26['workplace_notification']}",
    }

    def _describe(self, status: str, sub_checks: dict[str, bool]) -> str:
        if status == "PASS":
            return (
                "Deployer obligations satisfied: usage instructions followed,"
                " human oversight assigned, monitoring in place, persons"
                " informed, workplace notified."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Deployer obligation gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict[str, bool]) -> str:
        actions: list[str] = []
        if not sub_checks["use_per_instructions"]:
            actions.append(
                "Provide instructions for use so deployers can operate"
                " the AI system correctly per Art. 26(1)."
            )
        if not sub_checks["human_oversight_assigned"]:
            actions.append(
                "Document human oversight assignment to competent persons"
                " per Art. 26(2)."
            )
        if not sub_checks["operation_monitoring"]:
            actions.append(
                "Implement operational monitoring and logging to detect"
                " anomalies per Art. 26(5)."
            )
        if not sub_checks["persons_informed"]:
            actions.append(
                "Create an AI disclosure document informing affected persons"
                " about AI system use per Art. 26(7)."
            )
        if not sub_checks["workplace_notification"]:
            actions.append(
                "Inform workers' representatives about AI system use"
                " per Art. 26(7)."
            )
        return " ".join(actions)
