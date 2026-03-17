"""Drata GRC adapter — translates to Drata's evidence format.

Drata uses PASSING / FAILING / NOT_APPLICABLE status enums.

Control IDs are placeholders until Drata API research (Week 2).
"""

from __future__ import annotations

from app.schemas.compliance import AssessmentResult, ComplianceCheck
from app.services.grc.control_mappings import DRATA_CONTROL_MAP

_STATUS_MAP: dict[str, str] = {
    "PASS": "PASSING",
    "FAIL": "FAILING",
    "PARTIAL": "FAILING",  # Drata has no partial — map to FAILING
}


class DrataAdapter:
    """Drata-specific GRC payload adapter."""

    def platform_name(self) -> str:
        return "drata"

    def control_mapping(self) -> dict[str, str]:
        return DRATA_CONTROL_MAP

    def translate(self, result: AssessmentResult) -> dict:
        controls = [self._translate_check(c) for c in result.checks]
        return {
            "platform": "drata",
            "schema_version": "1.0",
            "assessment_id": result.assessment_id,
            "generated_at": result.generated_at.isoformat(),
            "controls": controls,
        }

    def _translate_check(self, check: ComplianceCheck) -> dict:
        control_id = DRATA_CONTROL_MAP.get(check.rule_id, check.rule_id)
        return {
            "control_id": control_id,
            "control_name": check.rule_name,
            "framework": "EU_AI_ACT",
            "status": _STATUS_MAP.get(check.status, check.status),
            "evidence": {
                "type": "automated_evidence",
                "source": "auditlens",
                "description": check.evidence.description,
                "tested_at": check.evidence.checked_at.isoformat(),
            },
        }
