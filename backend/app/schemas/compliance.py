"""Compliance output models — the core deliverable.

These models define the standardized JSON payload that GRC platforms consume.
The schema matches CLAUDE.md Section 6 (Output JSON Schema).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

SeverityLiteral = Literal["critical", "high", "medium", "low", "info"]
StatusLiteral = Literal["PASS", "FAIL", "PARTIAL", "N/A"]
RoleLiteral = Literal[
    "provider", "deployer", "both", "gpai", "gpai_systemic",
    "library", "tool", "undeclared",
]


class CheckEvidence(BaseModel):
    """Evidence supporting a compliance check result."""

    description: str
    source: str
    evidence_url: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SubCheckDetail(BaseModel):
    """Rich detail for a single sub-check within an article assessment."""

    id: str
    description: str
    passed: bool
    reasoning: str
    locations: list[str] = Field(default_factory=list)
    article_reference: str = ""


class ComplianceCheck(BaseModel):
    """Result of a single article compliance check."""

    rule_id: str
    rule_name: str
    article: str
    status: StatusLiteral
    severity: SeverityLiteral
    evidence: CheckEvidence
    details: dict[str, bool | str | int | float | dict | None]
    remediation: str | None = None
    reasoning: str | None = None
    evidence_locations: list[str] = Field(default_factory=list)
    sub_checks: list[SubCheckDetail] = Field(default_factory=list)
    evidence_source: str = "repo_scan"
    is_applicable: bool = True


class ComplianceSummary(BaseModel):
    """Aggregated summary of all compliance checks."""

    total_checks: int
    passed: int
    failed: int
    partial: int
    compliance_score: int = Field(ge=0, le=100)
    overall_status: Literal[
        "COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT"
    ]
    critical_failures: list[str]


class AssessmentResult(BaseModel):
    """Complete compliance assessment — the top-level API response."""

    schema_version: str = "1.0"
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    checks: list[ComplianceCheck]
    summary: ComplianceSummary
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    risk_tier: str | None = None
    applicable_articles: list[str] | None = None
    advisory_checks: list[ComplianceCheck] | None = None

    # Role-based scoping (from scan request)
    role: str = "undeclared"
    sme: bool = False
    role_declared: bool = False  # True when role != "undeclared"
