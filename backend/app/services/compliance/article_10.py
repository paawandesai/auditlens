"""Article 10 — Data Governance compliance check.

EU AI Act Article 10 requires that training, validation, and testing data sets
shall be "relevant, sufficiently representative, and to the best extent possible,
free of errors and complete."

Sub-checks:
1. provenance_documented — training data sources are documented
2. class_balance_ok — protected attributes within acceptable threshold
3. data_quality_metrics_logged — quality metrics exist and are recorded
4. preprocessing_documented — data preprocessing steps are recorded

Threshold decision: Class balance uses a 60/40 split threshold. Any protected
attribute with a worse ratio than 60/40 is flagged as imbalanced. This aligns
with the "sufficiently representative" requirement without being so strict
that legitimate datasets are flagged.
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput, TrainingDataStats

# Class balance threshold: max allowed percentage for the majority class
CLASS_BALANCE_THRESHOLD = 60


class Article10Check:
    """Data Governance compliance check per EU AI Act Article 10."""

    rule_id: str = "EU_AI_ART_10"
    rule_name: str = "Data Governance"
    article: str = "Article 10"
    severity: SeverityLiteral = "critical"

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        """Evaluate data governance compliance from scanner output."""
        stats = scanner_output.training_data_stats or TrainingDataStats()

        provenance = self._check_provenance(scanner_output, stats)
        balance, imbalance_details = self._check_class_balance(stats)
        quality = stats.quality_metrics_logged
        preprocessing = stats.preprocessing_documented

        sub_checks: dict[str, bool] = {
            "provenance_documented": provenance,
            "class_balance_ok": balance,
            "data_quality_metrics_logged": quality,
            "preprocessing_documented": preprocessing,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        total = 4

        if passed == total:
            status = "PASS"
        elif passed == 0:
            status = "FAIL"
        else:
            status = "PARTIAL"

        remediation = self._build_remediation(
            provenance, balance, quality, preprocessing, imbalance_details
        )

        # Keep sub_checks strictly dict[str, bool]; imbalance_details goes separately
        details: dict[str, bool | str | int | float | dict | None] = {
            **sub_checks,
        }
        if imbalance_details:
            details["imbalance_details"] = imbalance_details

        return ComplianceCheck(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            article=self.article,
            status=status,
            severity=self.severity,
            evidence=CheckEvidence(
                description=self._build_evidence_description(status, sub_checks),
                source=f"scan://{scanner_output.repo_url}",
            ),
            details=details,
            remediation=remediation if status != "PASS" else None,
        )

    def _check_provenance(
        self, scanner_output: ScannerOutput, stats: TrainingDataStats
    ) -> bool:
        """Check if training data provenance is documented."""
        return stats.provenance_documented or scanner_output.has_data_documentation

    def _check_class_balance(
        self, stats: TrainingDataStats
    ) -> tuple[bool, dict | None]:
        """Check if protected attributes are within acceptable balance threshold.

        Returns (is_balanced, imbalance_details_or_none).
        """
        class_balance = stats.class_balance
        if not class_balance:
            return False, None

        for attribute, distribution in class_balance.items():
            if len(distribution) < 2:
                continue

            values = list(distribution.values())
            total = sum(values)
            if total == 0:
                continue

            max_pct = (max(values) / total) * 100

            if max_pct > CLASS_BALANCE_THRESHOLD:
                majority_key = max(distribution, key=distribution.get)  # type: ignore[arg-type]
                return False, {
                    "attribute": attribute,
                    "ratio": f"{round(max_pct)}/{round(100 - max_pct)}",
                    "majority_class": majority_key,
                }

        return True, None

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "provenance_documented": "no data provenance documentation",
        "class_balance_ok": "no class balance data or imbalanced classes",
        "data_quality_metrics_logged": "no data quality metrics logged",
        "preprocessing_documented": "no preprocessing documentation",
    }

    def _build_evidence_description(
        self, status: str, sub_checks: dict[str, bool]
    ) -> str:
        """Build a human-readable evidence description."""
        if status == "PASS":
            return (
                "Training data governance requirements satisfied:"
                " provenance documented, class balance within thresholds,"
                " quality metrics logged, preprocessing documented."
            )

        failures = [
            self._FAILURE_DESCRIPTIONS.get(name, name.replace("_", " "))
            for name, val in sub_checks.items()
            if not val
        ]
        return f"Data governance gaps found: {', '.join(failures)}."

    def _build_remediation(
        self,
        provenance: bool,
        balance: bool,
        quality: bool,
        preprocessing: bool,
        imbalance_details: dict | None,
    ) -> str:
        """Build actionable remediation guidance."""
        actions = []

        if not provenance:
            actions.append(
                "Document training data sources, provenance chain,"
                " and collection methodology."
            )
        if not balance:
            if imbalance_details:
                attr = imbalance_details["attribute"]
                ratio = imbalance_details["ratio"]
                actions.append(
                    f"Address {attr} class imbalance ({ratio})"
                    " through resampling or re-collection."
                )
            else:
                actions.append(
                    "Provide class balance statistics for protected"
                    " attributes in training data."
                )
        if not quality:
            actions.append(
                "Log data quality metrics (completeness, consistency, accuracy)."
            )
        if not preprocessing:
            actions.append(
                "Document all data preprocessing and transformation steps."
            )

        return " ".join(actions) if actions else ""
