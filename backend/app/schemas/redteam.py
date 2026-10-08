"""Red team scan input models — adversarial testing results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class ComplianceRef(BaseModel):
    """Reference to a specific compliance framework requirement."""

    framework: str  # "eu_ai_act"
    reference: str  # "Article 9"
    requirement: str = ""  # "9(2)(a)"


class RedTeamFinding(BaseModel):
    """A single adversarial test finding."""

    finding_id: str = ""
    category: str  # "prompt-injection-rag"
    subcategory: str = ""
    severity: int  # 1-5
    grade: Literal["pass", "partial_fail", "fail", "critical_fail"]
    confidence: float = 0.9
    reasoning: str = ""
    compliance_refs: list[ComplianceRef] = []

    @field_validator("category")
    @classmethod
    def _canonical_category(cls, value: str) -> str:
        # redteam-engine emits snake_case enum values ("tool_misuse"); the
        # mapper keys on kebab-case ("tool-misuse"). Accept both.
        return value.strip().lower().replace("_", "-")


class RedTeamScanResult(BaseModel):
    """Complete red team scan result for ingestion."""

    scan_id: str
    timestamp: str = ""
    target: dict = {}
    summary: dict = {}
    findings: list[RedTeamFinding]
