"""Article 72 — Post-Market Monitoring by Providers.

EU AI Act Article 72 requires providers of high-risk AI systems to establish
and document a post-market monitoring system that is proportionate to the
nature and risks of the AI system. The monitoring plan must be part of the
technical documentation referred to in Annex IV.

Sub-checks:
1. monitoring_system — has_monitoring_config
2. monitoring_plan — has_monitoring_config AND has_logging_config
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_72


class Article72Check:
    """Post-Market Monitoring compliance check per EU AI Act Article 72."""

    rule_id: str = "EU_AI_ART_72"
    rule_name: str = "Post-Market Monitoring"
    article: str = "Article 72"
    severity: SeverityLiteral = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        monitoring_system = scanner_output.has_monitoring_config
        monitoring_plan = (
            scanner_output.has_monitoring_config and scanner_output.has_logging_config
        )

        sub_checks_raw: dict[str, bool] = {
            "monitoring_system": monitoring_system,
            "monitoring_plan": monitoring_plan,
        }

        sub_check_meta: dict[str, tuple[str, list[str], str]] = {
            "monitoring_system": (
                "Post-market monitoring system established proportionate to risks",
                ["docs/monitoring*", "monitoring.yaml", "monitoring.conf", ".github/workflows/*"],
                ART_72["monitoring_system"],
            ),
            "monitoring_plan": (
                "Post-market monitoring plan documented and kept up to date",
                ["docs/monitoring*", "monitoring.yaml", "logging.conf", "logging.yaml"],
                ART_72["monitoring_plan"],
            ),
        }

        # Map sub-check IDs to scanner field names for matched_paths lookup.
        scanner_field_map: dict[str, list[str]] = {
            "monitoring_system": ["has_monitoring_config"],
            "monitoring_plan": ["has_monitoring_config", "has_logging_config"],
        }

        sub_checks: list[SubCheckDetail] = []
        evidence_locations: list[str] = []

        for check_id, passed in sub_checks_raw.items():
            description, default_locations, article_ref = sub_check_meta[check_id]
            scanner_fields = scanner_field_map[check_id]
            actual_paths: list[str] = []
            for sf in scanner_fields:
                actual_paths.extend(scanner_output.matched_paths.get(sf, []))

            if check_id == "monitoring_plan" and not passed:
                missing = []
                if not scanner_output.has_monitoring_config:
                    missing.append("monitoring configuration")
                if not scanner_output.has_logging_config:
                    missing.append("logging configuration")
                reasoning = (
                    f"Missing: {', '.join(missing)}."
                    f" A monitoring plan requires both monitoring and logging."
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
            "Article 72 requires providers to establish a post-market monitoring"
            " system that actively collects, documents, and analyses data on"
            " the AI system's performance throughout its lifecycle. The monitoring"
            " plan must be documented as part of the technical documentation"
            f" (Annex IV). {passed_count}/{total} monitoring components evidenced."
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
        "monitoring_system": f"no monitoring system — {ART_72['monitoring_system']}",
        "monitoring_plan": f"no monitoring plan — {ART_72['monitoring_plan']}",
    }

    def _describe(self, status: str, sub_checks: dict[str, bool]) -> str:
        if status == "PASS":
            return (
                "Post-market monitoring obligations satisfied: monitoring system"
                " established and monitoring plan documented."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Post-market monitoring gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict[str, bool]) -> str:
        actions: list[str] = []
        if not sub_checks["monitoring_system"]:
            actions.append(
                "Establish a post-market monitoring system proportionate to"
                " the nature and risks of the AI system per Art. 72(1)."
            )
        if not sub_checks["monitoring_plan"]:
            actions.append(
                "Document a post-market monitoring plan covering data collection,"
                " analysis methodology, and update procedures per Art. 72(2)."
                " Include both monitoring and logging configurations."
            )
        return " ".join(actions)
