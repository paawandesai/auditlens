"""Article 6 — Classification Rules for High-Risk AI Systems.

EU AI Act Article 6 defines when an AI system is classified as high-risk:
- Art. 6(1): Safety component of a product under Annex I harmonisation legislation
- Art. 6(2): AI system listed in Annex III high-risk use cases
- Art. 6(3): Exception for AI that does not pose significant risk

This check reports the risk classification result as a compliance assessment,
using signals already computed by the scanner's risk_classifier.

Sub-checks:
1. annex_iii_classification — whether Annex III domains detected
2. safety_component_assessment — whether risk/safety documentation exists
3. risk_level_determined — whether risk classification was computed
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_6


class Article06Check:
    """Classification Rules compliance check per EU AI Act Article 6."""

    rule_id: str = "EU_AI_ART_6"
    rule_name: str = "Classification Rules for High-Risk AI"
    article: str = "Article 6"
    severity: SeverityLiteral = "high"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "annex_iii_classification": (
            "Annex III high-risk use case classification assessed",
            ["README.md", "docs/*"],
            ART_6["annex_iii"],
        ),
        "safety_component_assessment": (
            "Safety component risk assessment documented",
            ["RISK_ASSESSMENT.md", "risk_assessment/*", "docs/safety/*"],
            ART_6["safety_component"],
        ),
        "risk_level_determined": (
            "Risk level classification determined for the AI system",
            ["docs/risk/*", "README.md"],
            ART_6["risk_determined"],
        ),
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        # Sub-check 1: Annex III domain detection
        has_domains = bool(scanner_output.detected_domains)

        # Sub-check 2: Safety/risk documentation exists
        has_safety_docs = scanner_output.has_risk_assessment

        # Sub-check 3: Risk classification was computed
        has_classification = scanner_output.risk_classification is not None

        sub_checks_dict = {
            "annex_iii_classification": has_domains,
            "safety_component_assessment": has_safety_docs,
            "risk_level_determined": has_classification,
        }

        passed = sum(1 for v in sub_checks_dict.values() if v)
        total = len(sub_checks_dict)
        status = "PASS" if passed == total else ("FAIL" if passed == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks_dict) if status != "PASS" else None

        # Build rich sub-checks
        rich_sub_checks: list[SubCheckDetail] = []

        # Annex III classification
        domain_paths = scanner_output.matched_paths.get("detected_domains", [])
        if has_domains:
            domain_names = [d.domain for d in scanner_output.detected_domains]
            categories = [d.annex_iii_category for d in scanner_output.detected_domains]
            annex_reasoning = (
                f"Annex III domains detected: {', '.join(domain_names)} "
                f"(categories: {', '.join(categories)})"
            )
        else:
            annex_reasoning = (
                "No Annex III high-risk domains detected in repository content. "
                "The system may still be high-risk under Art. 6(1) if it is a safety component."
            )
        rich_sub_checks.append(SubCheckDetail(
            id="annex_iii_classification",
            description=self._SUB_CHECK_META["annex_iii_classification"][0],
            passed=has_domains,
            reasoning=annex_reasoning,
            locations=domain_paths if has_domains else ["README.md", "docs/*"],
            article_reference=ART_6["annex_iii"],
        ))

        # Safety component
        safety_paths = scanner_output.matched_paths.get("has_risk_assessment", [])
        rich_sub_checks.append(SubCheckDetail(
            id="safety_component_assessment",
            description=self._SUB_CHECK_META["safety_component_assessment"][0],
            passed=has_safety_docs,
            reasoning=(
                f"Found: {', '.join(safety_paths)}"
                if has_safety_docs and safety_paths
                else "Evidence detected via content analysis — safety component risk assessment documented."
                if has_safety_docs
                else "No risk/safety assessment found. Expected: RISK_ASSESSMENT.md, docs/safety/*."
            ),
            locations=safety_paths if has_safety_docs and safety_paths else ["RISK_ASSESSMENT.md", "risk_assessment/*", "docs/safety/*"],
            article_reference=ART_6["safety_component"],
        ))

        # Risk level determined
        if has_classification:
            rc = scanner_output.risk_classification
            class_reasoning = (
                f"Risk classification computed: {rc.risk_level} "
                f"(score: {rc.risk_score}/100, confidence: {rc.confidence:.0%})"
            )
            if rc.annex_iii_category:
                class_reasoning += f", Annex III category: {rc.annex_iii_category}"
        else:
            class_reasoning = (
                "Risk classification could not be determined. "
                "Insufficient signals (no frameworks or domains detected)."
            )
        rich_sub_checks.append(SubCheckDetail(
            id="risk_level_determined",
            description=self._SUB_CHECK_META["risk_level_determined"][0],
            passed=has_classification,
            reasoning=class_reasoning,
            locations=[],
            article_reference=ART_6["risk_determined"],
        ))

        evidence_locations = [
            path
            for sc in rich_sub_checks
            if sc.passed
            for path in sc.locations
        ]

        # Build risk level string for reasoning
        risk_str = "UNDETERMINED"
        if has_classification and scanner_output.risk_classification:
            risk_str = scanner_output.risk_classification.risk_level

        overall_reasoning = (
            f"Article 6 determines whether an AI system is classified as high-risk "
            f"under the EU AI Act, based on Annex III use cases or Annex I safety "
            f"component status. Classification result: {risk_str}. "
            f"{passed}/{total} classification signals present."
        )

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._describe(status, sub_checks_dict, risk_str),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=sub_checks_dict,
            remediation=remediation,
            reasoning=overall_reasoning,
            evidence_locations=evidence_locations,
            sub_checks=rich_sub_checks,
        )

    def _describe(self, status: str, sub_checks: dict, risk_level: str) -> str:
        if status == "PASS":
            return (
                f"AI system classification complete. Risk level: {risk_level}. "
                "Annex III domains identified, safety assessment documented, "
                "and risk classification computed."
            )
        failures = [k.replace("_", " ") for k, v in sub_checks.items() if not v]
        return (
            f"Classification gaps (risk level: {risk_level}): "
            f"{', '.join(failures)}."
        )

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["annex_iii_classification"]:
            actions.append(
                "Document the AI system's intended use case and determine whether "
                "it falls under Annex III high-risk categories per Art. 6(2)."
            )
        if not sub_checks["safety_component_assessment"]:
            actions.append(
                "Assess whether the AI system is a safety component of a product "
                "covered by Annex I harmonisation legislation per Art. 6(1). "
                "Document the assessment in a risk assessment file."
            )
        if not sub_checks["risk_level_determined"]:
            actions.append(
                "Ensure the AI system's risk level can be determined. "
                "Add framework dependencies and domain documentation "
                "so the classifier can compute a risk score."
            )
        return " ".join(actions)
