"""Article 8 — Compliance with Requirements (meta-check).

EU AI Act Article 8 requires that high-risk AI systems be designed and
developed in such a way that they comply with the requirements set out in
Articles 9-15, taking into account their intended purpose and the generally
acknowledged state of the art.

Sub-checks:
1. risk_management — Art. 9 signal (has_risk_assessment)
2. data_governance — Art. 10 signal (has_data_documentation)
3. technical_docs — Art. 11 signal (has_model_card)
4. record_keeping — Art. 12 signal (has_logging_config)
5. transparency — Art. 13 signal (has_explainability)
6. human_oversight — Art. 14 signal (has_human_oversight_docs)
7. accuracy_robustness — Art. 15 signal (has_test_suite)
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_8


class Article08Check:
    """Compliance with Requirements meta-check per EU AI Act Article 8."""

    rule_id: str = "EU_AI_ART_8"
    rule_name: str = "Compliance with Requirements"
    article: str = "Article 8"
    severity: SeverityLiteral = "high"

    _SUB_CHECK_MAP: dict[str, tuple[str, str, list[str], str]] = {
        "risk_management": (
            "has_risk_assessment",
            "Risk management system documented (Art. 9 proxy)",
            ["RISK_ASSESSMENT.md", "risk_assessment/*", "docs/risk*"],
            ART_8["compliance"],
        ),
        "data_governance": (
            "has_data_documentation",
            "Data governance documentation present (Art. 10 proxy)",
            ["data_card*", "dataset_card*", "datasheet*"],
            ART_8["compliance"],
        ),
        "technical_docs": (
            "has_model_card",
            "Technical documentation / model card present (Art. 11 proxy)",
            ["MODEL_CARD*", "model_card*", "docs/model*"],
            ART_8["compliance"],
        ),
        "record_keeping": (
            "has_logging_config",
            "Automatic logging / record-keeping configured (Art. 12 proxy)",
            ["logging.conf", "logging.yaml", ".github/workflows/*"],
            ART_8["compliance"],
        ),
        "transparency": (
            "has_explainability",
            "Transparency / explainability documentation present (Art. 13 proxy)",
            ["docs/explainability*", "SHAP*", "LIME*"],
            ART_8["compliance"],
        ),
        "human_oversight": (
            "has_human_oversight_docs",
            "Human oversight documentation present (Art. 14 proxy)",
            ["docs/human_oversight*", "HUMAN_REVIEW*"],
            ART_8["compliance"],
        ),
        "accuracy_robustness": (
            "has_test_suite",
            "Test suite present for accuracy and robustness (Art. 15 proxy)",
            ["tests/", "test/", "spec/"],
            ART_8["compliance"],
        ),
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        sub_checks: list[SubCheckDetail] = []
        evidence_locations: list[str] = []
        details: dict[str, bool | str | int | float | dict | None] = {}

        for check_id, (attr, description, default_locations, article_ref) in self._SUB_CHECK_MAP.items():
            passed = getattr(scanner_output, attr, False)
            details[check_id] = passed
            actual_paths = scanner_output.matched_paths.get(attr, [])

            reasoning = (
                f"Found: {', '.join(actual_paths)}"
                if passed and actual_paths
                else f"Evidence detected via content analysis — {description.lower()}"
                if passed
                else f"Signal '{attr}' not found — expected files: {', '.join(default_locations)}."
            )

            sub_checks.append(SubCheckDetail(
                id=check_id,
                description=description,
                passed=passed,
                reasoning=reasoning,
                locations=actual_paths if passed and actual_paths else default_locations,
                article_reference=article_ref,
            ))

            if passed:
                evidence_locations.extend(actual_paths if actual_paths else default_locations)

        passed_count = sum(1 for sc in sub_checks if sc.passed)

        if passed_count >= 5:
            status = "PASS"
        elif passed_count >= 2:
            status = "PARTIAL"
        else:
            status = "FAIL"

        remediation = self._build_remediation(sub_checks) if status != "PASS" else None

        overall_reasoning = (
            "Article 8 is a meta-requirement. It passes when the AI system is"
            " designed to comply with Articles 9-15, considering its intended"
            f" purpose. {passed_count}/7 sub-requirements satisfied."
        )

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._describe(status, passed_count),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=details,
            remediation=remediation,
            reasoning=overall_reasoning,
            evidence_locations=evidence_locations,
            sub_checks=sub_checks,
        )

    def _describe(self, status: str, passed_count: int) -> str:
        if status == "PASS":
            return (
                "AI system demonstrates compliance with Articles 9-15 requirements."
                f" {passed_count}/7 sub-requirements satisfied."
            )
        return (
            f"Incomplete compliance with Articles 9-15: {passed_count}/7"
            " sub-requirements satisfied."
        )

    def _build_remediation(self, sub_checks: list[SubCheckDetail]) -> str:
        actions: list[str] = []
        article_map = {
            "risk_management": ("Art. 9", "risk management system"),
            "data_governance": ("Art. 10", "data governance documentation"),
            "technical_docs": ("Art. 11", "technical documentation / model card"),
            "record_keeping": ("Art. 12", "automatic logging configuration"),
            "transparency": ("Art. 13", "transparency / explainability documentation"),
            "human_oversight": ("Art. 14", "human oversight documentation"),
            "accuracy_robustness": ("Art. 15", "test suite for accuracy and robustness"),
        }
        for sc in sub_checks:
            if not sc.passed and sc.id in article_map:
                art, desc = article_map[sc.id]
                actions.append(f"Add {desc} to satisfy {art}.")
        return " ".join(actions)
