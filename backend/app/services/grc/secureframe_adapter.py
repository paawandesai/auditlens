"""Secureframe GRC adapter — translates to Secureframe's evidence format.

Secureframe uses met / not_met / partially_met status enums.

Control IDs are placeholders until Secureframe API research (Week 2).
"""

from __future__ import annotations

from app.schemas.compliance import AssessmentResult, ComplianceCheck
from app.services.grc.control_mappings import SECUREFRAME_CONTROL_MAP

_STATUS_MAP: dict[str, str] = {
    "PASS": "met",
    "FAIL": "not_met",
    "PARTIAL": "partially_met",
}


class SecureframeAdapter:
    """Secureframe-specific GRC payload adapter."""

    def platform_name(self) -> str:
        return "secureframe"

    def control_mapping(self) -> dict[str, str]:
        return SECUREFRAME_CONTROL_MAP

    def translate(self, result: AssessmentResult) -> dict:
        controls = [self._translate_check(c) for c in result.checks]
        return {
            "platform": "secureframe",
            "schema_version": "1.0",
            "assessment_id": result.assessment_id,
            "generated_at": result.generated_at.isoformat(),
            "controls": controls,
        }

    def _translate_check(self, check: ComplianceCheck) -> dict:
        control_id = SECUREFRAME_CONTROL_MAP.get(check.rule_id, check.rule_id)
        return {
            "control_id": control_id,
            "control_name": check.rule_name,
            "framework": "EU_AI_ACT",
            "status": _STATUS_MAP.get(check.status, check.status),
            "evidence": {
                "type": "integration_test",
                "source": "auditlens",
                "details": check.evidence.description,
                "evaluated_at": check.evidence.checked_at.isoformat(),
            },
        }
