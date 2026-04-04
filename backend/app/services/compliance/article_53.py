"""Article 53 — Obligations for Providers of General-Purpose AI Models.

EU AI Act Article 53 sets out obligations for providers of general-purpose AI
(GPAI) models, including maintaining technical documentation, providing
downstream information, complying with copyright law, and publishing a training
data summary.

Sub-checks:
1. technical_docs_maintained — has_model_card AND has_architecture_docs
2. downstream_info_provided — has_user_instructions
3. copyright_compliance — has_copyright_policy
4. training_summary_published — has_data_documentation
"""

from __future__ import annotations

from app.schemas.compliance import (
    CheckEvidence,
    ComplianceCheck,
    SeverityLiteral,
    SubCheckDetail,
)
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_53


class Article53Check:
    """General-Purpose AI Obligations per EU AI Act Article 53."""

    rule_id: str = "EU_AI_ART_53"
    rule_name: str = "General-Purpose AI Obligations"
    article: str = "Article 53"
    severity: SeverityLiteral = "high"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        technical_docs = (
            scanner_output.has_model_card and scanner_output.has_architecture_docs
        )
        downstream_info = scanner_output.has_user_instructions
        copyright_compliance = scanner_output.has_copyright_policy
        training_summary = scanner_output.has_data_documentation

        sub_checks_raw: dict[str, bool] = {
            "technical_docs_maintained": technical_docs,
            "downstream_info_provided": downstream_info,
            "copyright_compliance": copyright_compliance,
            "training_summary_published": training_summary,
        }

        sub_check_meta: dict[str, tuple[str, list[str], str]] = {
            "technical_docs_maintained": (
                "Technical documentation maintained and kept up to date",
                ["MODEL_CARD*", "model_card*", "ARCHITECTURE*", "docs/architecture*"],
                ART_53["technical_docs"],
            ),
            "downstream_info_provided": (
                "Information and documentation provided to downstream AI system providers",
                ["USAGE*", "user_guide*", "deployer_guide*", "docs/integration*"],
                ART_53["downstream_info"],
            ),
            "copyright_compliance": (
                "Policy to comply with Union copyright law documented",
                ["LICENSE*", "COPYRIGHT*", "docs/copyright*", "copyright_policy*"],
                ART_53["copyright"],
            ),
            "training_summary_published": (
                "Detailed summary of training content published",
                ["data_card*", "dataset_card*", "datasheet*", "docs/training_data*"],
                ART_53["training_summary"],
            ),
        }

        # Map sub-check IDs to scanner field names for matched_paths lookup.
        scanner_field_map: dict[str, list[str]] = {
            "technical_docs_maintained": ["has_model_card", "has_architecture_docs"],
            "downstream_info_provided": ["has_user_instructions"],
            "copyright_compliance": ["has_copyright_policy"],
            "training_summary_published": ["has_data_documentation"],
        }

        sub_checks: list[SubCheckDetail] = []
        evidence_locations: list[str] = []

        for check_id, passed in sub_checks_raw.items():
            description, default_locations, article_ref = sub_check_meta[check_id]
            scanner_fields = scanner_field_map[check_id]
            actual_paths: list[str] = []
            for sf in scanner_fields:
                actual_paths.extend(scanner_output.matched_paths.get(sf, []))
            reasoning = (
                f"Found: {', '.join(actual_paths)}"
                if passed and actual_paths
                else f"Evidence detected via content analysis — {description.lower()}"
                if passed
                else f"No evidence for {check_id.replace('_', ' ')} — "
                     f"expected files: {', '.join(default_locations)}."
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

        passed_count = sum(1 for v in sub_checks_raw.values() if v)
        total = len(sub_checks_raw)
        status = "PASS" if passed_count == total else ("FAIL" if passed_count == 0 else "PARTIAL")

        remediation = self._build_remediation(sub_checks_raw) if status != "PASS" else None

        overall_reasoning = (
            "Article 53 applies to providers of general-purpose AI (GPAI)"
            " models — also known as foundation models. These providers must"
            " maintain technical documentation, provide downstream integration"
            " information, comply with copyright law, and publish a sufficiently"
            f" detailed training data summary. {passed_count}/{total} GPAI"
            " obligations evidenced."
        )

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._describe(status, sub_checks_raw),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=sub_checks_raw,
            remediation=remediation,
            reasoning=overall_reasoning,
            evidence_locations=evidence_locations,
            sub_checks=sub_checks,
        )

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "technical_docs_maintained": f"no technical docs — {ART_53['technical_docs']}",
        "downstream_info_provided": f"no downstream info — {ART_53['downstream_info']}",
        "copyright_compliance": f"no copyright policy — {ART_53['copyright']}",
        "training_summary_published": f"no training summary — {ART_53['training_summary']}",
    }

    def _describe(self, status: str, sub_checks: dict[str, bool]) -> str:
        if status == "PASS":
            return (
                "GPAI provider obligations satisfied: technical documentation"
                " maintained, downstream information provided, copyright policy"
                " in place, training data summary published."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"GPAI obligation gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict[str, bool]) -> str:
        actions: list[str] = []
        if not sub_checks["technical_docs_maintained"]:
            actions.append(
                "Create and maintain a model card and architecture documentation"
                " per Art. 53(1)(a)."
            )
        if not sub_checks["downstream_info_provided"]:
            actions.append(
                "Provide integration instructions and documentation for downstream"
                " AI system providers per Art. 53(1)(b)."
            )
        if not sub_checks["copyright_compliance"]:
            actions.append(
                "Document a copyright compliance policy covering training data"
                " usage per Art. 53(1)(c)."
            )
        if not sub_checks["training_summary_published"]:
            actions.append(
                "Publish a sufficiently detailed summary of training content"
                " per Art. 53(1)(d)."
            )
        return " ".join(actions)
