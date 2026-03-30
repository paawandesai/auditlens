"""Article 50 — Transparency Obligations compliance check.

EU AI Act Article 50 requires transparency for AI systems interacting
with people. Applies to ALL AI systems regardless of risk level.

Sub-checks:
1. ai_interaction_disclosed — persons informed they interact with AI
2. synthetic_content_marked — AI-generated content is marked
3. provider_identified — provider name and contact accessible
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral, SubCheckDetail
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_50


class Article50Check:
    """Transparency Obligations compliance check per EU AI Act Article 50."""

    rule_id: str = "EU_AI_ART_50"
    rule_name: str = "Transparency Obligations"
    article: str = "Article 50"
    severity: SeverityLiteral = "high"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "ai_interaction_disclosed": (
            "Persons informed they interact with an AI system",
            ["README.md", "docs/transparency/*"],
            ART_50["ai_interaction_disclosed"],
        ),
        "synthetic_content_marked": (
            "AI-generated content marked in machine-readable format",
            ["docs/watermarking/*", "docs/content/*"],
            ART_50["synthetic_content_marked"],
        ),
        "provider_identified": (
            "Provider name and contact information accessible",
            ["README.md", "docs/provider/*"],
            ART_50["provider_identified"],
        ),
    }

    # Map sub-check IDs to scanner field names for matched_paths lookup.
    _SCANNER_FIELD_MAP: dict[str, str] = {
        "ai_interaction_disclosed": "has_ai_disclosure",
        "synthetic_content_marked": "has_synthetic_content_marking",
        "provider_identified": "has_provider_identification",
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        ai_disclosed = scanner_output.has_ai_disclosure
        synthetic_marked = scanner_output.has_synthetic_content_marking
        provider_id = scanner_output.has_provider_identification

        sub_checks = {
            "ai_interaction_disclosed": ai_disclosed,
            "synthetic_content_marked": synthetic_marked,
            "provider_identified": provider_id,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        total = len(sub_checks)
        status = "PASS" if passed == total else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

        rich_sub_checks: list[SubCheckDetail] = []
        for check_id, value in sub_checks.items():
            description, default_locations, article_ref = self._SUB_CHECK_META[check_id]
            scanner_field = self._SCANNER_FIELD_MAP[check_id]
            actual_paths = scanner_output.matched_paths.get(scanner_field, [])
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
            "Article 50 requires transparency for AI systems interacting with"
            " people, regardless of risk level. This repository shows"
            f" {passed} of {total} transparency obligation signals, indicating "
            + ("full" if passed == total else "partial" if passed > 0 else "no")
            + " transparency compliance."
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
        "ai_interaction_disclosed": (
            f"no AI interaction disclosure found — {ART_50['ai_interaction_disclosed']}"
        ),
        "synthetic_content_marked": (
            f"no synthetic content marking found — {ART_50['synthetic_content_marked']}"
        ),
        "provider_identified": (
            f"no provider identification found — {ART_50['provider_identified']}"
        ),
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Transparency obligations met: AI interaction disclosure,"
                " synthetic content marking, and provider identification found."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Transparency gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["ai_interaction_disclosed"]:
            actions.append(
                "Add clear disclosure that users are interacting with an AI"
                " system per Art. 50(1). Include in UI-facing files or docs."
            )
        if not sub_checks["synthetic_content_marked"]:
            actions.append(
                "Mark AI-generated content in a machine-readable format"
                " per Art. 50(2). Add watermarking or metadata tagging."
            )
        if not sub_checks["provider_identified"]:
            actions.append(
                "Ensure provider name, contact, and version are documented"
                " in README or user-facing docs per Art. 50(4)."
            )
        return " ".join(actions)
