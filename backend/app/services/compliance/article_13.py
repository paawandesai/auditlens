"""Article 13 — Transparency compliance check.

EU AI Act Article 13 requires AI systems to be designed and developed such
that their operation is sufficiently transparent to enable users to interpret
and use the system's output appropriately.

Sub-checks:
1. explainability_available — SHAP, LIME, or similar explainability tools present
2. feature_importance_documented — feature importance is documented
3. user_instructions_provided — instructions for use exist
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput


class Article13Check:
    """Transparency compliance check per EU AI Act Article 13."""

    rule_id: str = "EU_AI_ART_13"
    rule_name: str = "Transparency"
    article: str = "Article 13"
    severity: SeverityLiteral = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        explainability = scanner_output.has_explainability
        feature_importance = scanner_output.has_feature_importance_docs
        user_instructions = scanner_output.has_model_card

        sub_checks = {
            "explainability_available": explainability,
            "feature_importance_documented": feature_importance,
            "user_instructions_provided": user_instructions,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        status = "PASS" if passed == 3 else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

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
        )

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Transparency requirements met: explainability,"
                " feature importance, and user instructions available."
            )
        failures = [k.replace("_", " ") for k, v in sub_checks.items() if not v]
        return f"Transparency gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["explainability_available"]:
            actions.append("Add SHAP or LIME explainability analysis to the model.")
        if not sub_checks["feature_importance_documented"]:
            actions.append("Document feature importance rankings and their impact on predictions.")
        if not sub_checks["user_instructions_provided"]:
            actions.append(
                "Provide instructions for use describing the system's"
                " capabilities and limitations."
            )
        return " ".join(actions)
