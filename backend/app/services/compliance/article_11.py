"""Article 11 — Technical Documentation compliance check.

EU AI Act Article 11 requires technical documentation to be drawn up before
the AI system is placed on the market or put into service.

Sub-checks:
1. model_card_exists — model card or equivalent documentation found
2. architecture_documented — system architecture is documented
3. performance_recorded — performance metrics are recorded
4. development_process_documented — development methods and design specs [Annex IV §2]
5. standards_applied — harmonised standards listed [Annex IV §8]
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral, SubCheckDetail
from app.schemas.scanner import ScannerOutput
from app.services.compliance.citations import ART_11


class Article11Check:
    """Technical Documentation compliance check per EU AI Act Article 11."""

    rule_id: str = "EU_AI_ART_11"
    rule_name: str = "Technical Documentation"
    article: str = "Article 11"
    severity: SeverityLiteral = "critical"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "model_card_exists": (
            "Model card or equivalent technical documentation present",
            ["MODEL_CARD.md", "model_card/*"],
            ART_11["model_card"],
        ),
        "architecture_documented": (
            "System architecture documented",
            ["ARCHITECTURE.md", "docs/design/*", "docs/architecture/*"],
            ART_11["architecture"],
        ),
        "performance_recorded": (
            "Performance metrics recorded on test sets",
            ["eval_results/*", "metrics/*", "benchmark/*"],
            ART_11["performance"],
        ),
        "development_process_documented": (
            "Development methods and design specifications documented",
            ["docs/development/*", "docs/design/*"],
            ART_11["dev_process"],
        ),
        "standards_applied": (
            "Harmonised standards or common specifications listed",
            ["docs/standards/*", "docs/compliance/*"],
            ART_11["standards"],
        ),
    }

    # Map sub-check IDs to scanner field names for matched_paths lookup.
    _SCANNER_FIELD_MAP: dict[str, str] = {
        "model_card_exists": "has_model_card",
        "architecture_documented": "has_architecture_docs",
        "performance_recorded": "has_performance_metrics",
        "development_process_documented": "has_development_process_docs",
        "standards_applied": "has_standards_applied",
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        model_card = scanner_output.has_model_card
        architecture = scanner_output.has_architecture_docs
        performance = scanner_output.performance_metrics is not None
        dev_process = scanner_output.has_development_process_docs
        standards = scanner_output.has_standards_applied

        sub_checks = {
            "model_card_exists": model_card,
            "architecture_documented": architecture,
            "performance_recorded": performance,
            "development_process_documented": dev_process,
            "standards_applied": standards,
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
            "Article 11 requires technical documentation to be drawn up before the"
            " AI system is placed on the market. This repository shows"
            f" {passed} of {total} documentation signals, indicating "
            + ("full" if passed == total else "partial" if passed > 0 else "no")
            + " technical documentation."
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
        "model_card_exists": f"no model card — {ART_11['model_card']}",
        "architecture_documented": f"no architecture docs — {ART_11['architecture']}",
        "performance_recorded": f"no performance metrics — {ART_11['performance']}",
        "development_process_documented": f"no development process docs — {ART_11['dev_process']}",
        "standards_applied": f"no standards referenced — {ART_11['standards']}",
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Technical documentation complete: model card, architecture,"
                " performance metrics, development process, and standards present."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Technical documentation gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["model_card_exists"]:
            actions.append(
                "Create a model card documenting the AI system's purpose,"
                " design, and limitations per Art. 11(1) and Annex IV."
            )
        if not sub_checks["architecture_documented"]:
            actions.append(
                "Document system architecture including model type,"
                " training approach, and data flow per Annex IV §2(b)."
            )
        if not sub_checks["performance_recorded"]:
            actions.append(
                "Record performance metrics on test sets"
                " (accuracy, precision, recall, F1) per Annex IV §3."
            )
        if not sub_checks["development_process_documented"]:
            actions.append(
                "Document development methods, design specifications,"
                " and training methodology per Annex IV §2(a-c)."
            )
        if not sub_checks["standards_applied"]:
            actions.append(
                "List any harmonised standards or common specifications"
                " applied per Annex IV §8."
            )
        return " ".join(actions)
