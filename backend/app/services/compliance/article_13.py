"""Article 13 — Transparency compliance check.

EU AI Act Article 13 requires AI systems to be designed and developed such
that their operation is sufficiently transparent to enable users to interpret
and use the system's output appropriately.

Sub-checks:
1. explainability_available — SHAP, LIME, or similar explainability tools present
2. feature_importance_documented — feature importance is documented
3. user_instructions_provided — instructions for use exist
4. capabilities_limitations_stated — capabilities and limitations described [Art. 13(3)(b)]
5. group_performance_documented — performance for specific groups [Art. 13(3)(b)(v)]
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral, SubCheckDetail
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_13


class Article13Check:
    """Transparency compliance check per EU AI Act Article 13."""

    rule_id: str = "EU_AI_ART_13"
    rule_name: str = "Transparency"
    article: str = "Article 13"
    severity: SeverityLiteral = "high"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "explainability_available": (
            "Explainability tools (SHAP, LIME, or similar) present",
            ["docs/explainability/*", "*.py (SHAP/LIME imports)"],
            ART_13["explainability"],
        ),
        "feature_importance_documented": (
            "Feature importance rankings documented",
            ["docs/features/*", "docs/model/*"],
            ART_13["feature_importance"],
        ),
        "user_instructions_provided": (
            "Instructions for use provided to deployers",
            ["USAGE.md", "user_guide/*", "deployer_guide/*"],
            ART_13["user_instructions"],
        ),
        "capabilities_limitations_stated": (
            "Capabilities and known limitations described",
            ["MODEL_CARD.md", "docs/limitations/*"],
            ART_13["capabilities"],
        ),
        "group_performance_documented": (
            "Performance for specific groups of persons documented",
            ["docs/fairness/*", "docs/performance/*"],
            ART_13["group_performance"],
        ),
    }

    # Map sub-check IDs to scanner field names for matched_paths lookup.
    _SCANNER_FIELD_MAP: dict[str, list[str]] = {
        "explainability_available": ["has_explainability"],
        "feature_importance_documented": ["has_feature_importance_docs"],
        "user_instructions_provided": ["has_user_instructions", "has_model_card"],
        "capabilities_limitations_stated": ["has_capabilities_limitations"],
        "group_performance_documented": ["has_group_performance_docs"],
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        explainability = scanner_output.has_explainability
        feature_importance = scanner_output.has_feature_importance_docs
        user_instructions = scanner_output.has_user_instructions or scanner_output.has_model_card
        capabilities = scanner_output.has_capabilities_limitations
        group_performance = scanner_output.has_group_performance_docs

        sub_checks = {
            "explainability_available": explainability,
            "feature_importance_documented": feature_importance,
            "user_instructions_provided": user_instructions,
            "capabilities_limitations_stated": capabilities,
            "group_performance_documented": group_performance,
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
            "Article 13 requires AI systems to be sufficiently transparent to enable"
            " users to interpret and use outputs appropriately. This repository shows"
            f" {passed} of {total} transparency signals, indicating "
            + ("full" if passed == total else "partial" if passed > 0 else "no")
            + " transparency documentation."
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
        "explainability_available": f"no explainability tools — {ART_13['explainability']}",
        "feature_importance_documented": f"no feature importance docs — {ART_13['feature_importance']}",
        "user_instructions_provided": f"no user instructions — {ART_13['user_instructions']}",
        "capabilities_limitations_stated": f"no capabilities/limitations — {ART_13['capabilities']}",
        "group_performance_documented": f"no group performance data — {ART_13['group_performance']}",
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Transparency requirements met: explainability,"
                " feature importance, user instructions, capabilities/limitations,"
                " and group performance data available."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Transparency gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["explainability_available"]:
            actions.append(
                "Add SHAP or LIME explainability analysis per Art. 13(3)(d)."
            )
        if not sub_checks["feature_importance_documented"]:
            actions.append(
                "Document feature importance rankings and their impact"
                " on predictions per Art. 13(3)(b)(iv)."
            )
        if not sub_checks["user_instructions_provided"]:
            actions.append(
                "Provide instructions for use describing the system's"
                " capabilities and limitations per Art. 13(3)."
            )
        if not sub_checks["capabilities_limitations_stated"]:
            actions.append(
                "Document capabilities and known limitations"
                " per Art. 13(3)(b)."
            )
        if not sub_checks["group_performance_documented"]:
            actions.append(
                "Document performance for specific groups of persons"
                " per Art. 13(3)(b)(v)."
            )
        return " ".join(actions)
