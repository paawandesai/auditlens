"""Vanta GRC adapter — translates to Vanta's evidence format.

Vanta uses PASSING / FAILING / AT_RISK status enums and expects
evidence objects with specific fields for their dashboard.

Control IDs are placeholders until Vanta API research (Week 2).
"""

from __future__ import annotations

from app.schemas.compliance import AssessmentResult, ComplianceCheck
from app.services.grc.control_mappings import VANTA_CONTROL_MAP

_STATUS_MAP: dict[str, str] = {
    "PASS": "PASSING",
    "FAIL": "FAILING",
    "PARTIAL": "AT_RISK",
}


class VantaAdapter:
    """Vanta-specific GRC payload adapter."""

    def platform_name(self) -> str:
        return "vanta"

    def control_mapping(self) -> dict[str, str]:
        return VANTA_CONTROL_MAP

    def translate(self, result: AssessmentResult) -> dict:
        controls = [self._translate_check(c) for c in result.checks]
        return {
            "platform": "vanta",
            "schema_version": "1.0",
            "assessment_id": result.assessment_id,
            "generated_at": result.generated_at.isoformat(),
            "controls": controls,
        }

    def _translate_check(self, check: ComplianceCheck) -> dict:
        control_id = VANTA_CONTROL_MAP.get(check.rule_id, check.rule_id)
        return {
            "control_id": control_id,
            "control_name": check.rule_name,
            "framework": "EU_AI_ACT",
            "status": _STATUS_MAP.get(check.status, check.status),
            "evidence": {
                "type": "automated_test",
                "source": "auditlens",
                "result": check.evidence.description,
                "collected_at": check.evidence.checked_at.isoformat(),
            },
        }
