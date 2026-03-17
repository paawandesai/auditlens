"""Generic GRC adapter — universal format for unknown platforms.

Outputs a clean, standardized control-level payload that any
GRC platform can consume with minimal transformation.
"""

from __future__ import annotations

from app.schemas.compliance import AssessmentResult, ComplianceCheck
from app.services.grc.control_mappings import GENERIC_CONTROL_MAP

# Status mapping: our status → generic GRC status
_STATUS_MAP: dict[str, str] = {
    "PASS": "PASSING",
    "FAIL": "FAILING",
    "PARTIAL": "AT_RISK",
}


class GenericAdapter:
    """Universal GRC payload adapter."""

    def platform_name(self) -> str:
        return "generic"

    def control_mapping(self) -> dict[str, str]:
        return GENERIC_CONTROL_MAP

    def translate(self, result: AssessmentResult) -> dict:
        controls = [self._translate_check(c) for c in result.checks]
        return {
            "platform": "generic",
            "schema_version": "1.0",
            "assessment_id": result.assessment_id,
            "generated_at": result.generated_at.isoformat(),
            "summary": {
                "overall_status": result.summary.overall_status,
                "compliance_score": result.summary.compliance_score,
                "total_controls": result.summary.total_checks,
                "passing": result.summary.passed,
                "failing": result.summary.failed,
            },
            "controls": controls,
        }

    def _translate_check(self, check: ComplianceCheck) -> dict:
        control_id = GENERIC_CONTROL_MAP.get(check.rule_id, check.rule_id)
        return {
            "control_id": control_id,
            "control_name": check.rule_name,
            "framework": "EU_AI_ACT",
            "article": check.article,
            "status": _STATUS_MAP.get(check.status, check.status),
            "severity": check.severity,
            "evidence": {
                "type": "automated_scan",
                "source": "auditlens",
                "description": check.evidence.description,
                "collected_at": check.evidence.checked_at.isoformat(),
            },
            "remediation": check.remediation,
        }
