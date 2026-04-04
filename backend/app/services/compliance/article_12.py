"""Article 12 — Record-Keeping compliance check.

EU AI Act Article 12 requires automatic recording of events (logs) while
the high-risk AI system is operating.

Sub-checks:
1. logging_configured — logging/monitoring infrastructure exists
2. model_versioned — model versioning is in place
3. audit_trail_exists — audit trail for decisions exists
4. risk_situation_logging — logging of events identifying risk situations [Art. 12(2)(a)]
5. input_data_recording — recording of input data [Art. 12(3)(c)]
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral, SubCheckDetail
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_12


class Article12Check:
    """Record-Keeping compliance check per EU AI Act Article 12."""

    rule_id: str = "EU_AI_ART_12"
    rule_name: str = "Record-Keeping"
    article: str = "Article 12"
    severity: SeverityLiteral = "high"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "logging_configured": (
            "Logging/monitoring infrastructure configured",
            ["docs/logging/*", "logging.conf", "*.py (audit logging)"],
            ART_12["logging"],
        ),
        "model_versioned": (
            "Model versioning in place for traceability",
            [".github/workflows/*", ".dvc/*"],
            ART_12["versioning"],
        ),
        "audit_trail_exists": (
            "Audit trail linking inputs, outputs, and model versions",
            ["docs/logging/*", "logging.conf", ".github/workflows/*", ".dvc/*"],
            ART_12["audit_trail"],
        ),
        "risk_situation_logging": (
            "Logging of events identifying risk situations",
            ["docs/logging/*", "docs/monitoring/*"],
            ART_12["risk_events"],
        ),
        "input_data_recording": (
            "Recording of input data for which the system was used",
            ["docs/data_retention/*", "docs/logging/*"],
            ART_12["input_recording"],
        ),
    }

    # Map sub-check IDs to scanner field names for matched_paths lookup.
    _SCANNER_FIELD_MAP: dict[str, list[str]] = {
        "logging_configured": ["has_logging_config"],
        "model_versioned": ["has_versioning"],
        "audit_trail_exists": ["has_logging_config", "has_versioning"],
        "risk_situation_logging": ["has_risk_event_logging"],
        "input_data_recording": ["has_input_data_recording"],
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        logging = scanner_output.has_logging_config
        versioning = scanner_output.has_versioning
        audit_trail = logging and versioning  # audit trail requires both
        risk_events = scanner_output.has_risk_event_logging
        input_recording = scanner_output.has_input_data_recording

        sub_checks = {
            "logging_configured": logging,
            "model_versioned": versioning,
            "audit_trail_exists": audit_trail,
            "risk_situation_logging": risk_events,
            "input_data_recording": input_recording,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        total = len(sub_checks)
        status = "PASS" if passed == total else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

        rich_sub_checks: list[SubCheckDetail] = []
        for check_id, value in sub_checks.items():
            description, default_locations, article_ref = self._SUB_CHECK_META[check_id]
            scanner_fields = self._SCANNER_FIELD_MAP[check_id]
            actual_paths: list[str] = []
            for sf in scanner_fields:
                actual_paths.extend(scanner_output.matched_paths.get(sf, []))
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
            "Article 12 requires automatic recording of events (logs) while the"
            " high-risk AI system is operating. This repository shows"
            f" {passed} of {total} record-keeping signals, indicating "
            + ("full" if passed == total else "partial" if passed > 0 else "no")
            + " record-keeping infrastructure."
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
        "logging_configured": f"no logging configured — {ART_12['logging']}",
        "model_versioned": f"no model versioning — {ART_12['versioning']}",
        "audit_trail_exists": f"no audit trail — {ART_12['audit_trail']}",
        "risk_situation_logging": f"no risk event logging — {ART_12['risk_events']}",
        "input_data_recording": f"no input data recording — {ART_12['input_recording']}",
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Record-keeping requirements met: logging, versioning,"
                " audit trail, risk event logging, and input recording in place."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Record-keeping gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["logging_configured"]:
            actions.append(
                "Configure logging infrastructure to record AI system"
                " events per Art. 12(1)."
            )
        if not sub_checks["model_versioned"]:
            actions.append(
                "Implement model versioning to track changes"
                " per Art. 12(2)."
            )
        if not sub_checks["audit_trail_exists"]:
            actions.append(
                "Establish an audit trail linking inputs, outputs,"
                " and model versions per Art. 12(1)."
            )
        if not sub_checks["risk_situation_logging"]:
            actions.append(
                "Log events that identify risk situations"
                " per Art. 12(2)(a)."
            )
        if not sub_checks["input_data_recording"]:
            actions.append(
                "Record input data for which the system was used"
                " per Art. 12(3)(c)."
            )
        return " ".join(actions)
