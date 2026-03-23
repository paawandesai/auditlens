"""Article 10 — Data Governance compliance check.

EU AI Act Article 10 requires that training, validation, and testing data sets
shall be "relevant, sufficiently representative, and to the best extent possible,
free of errors and complete."

Sub-checks:
1. provenance_documented — training data sources are documented
2. bias_examined — bias analysis conducted per Art 10.2(f-g)
3. data_quality_metrics_logged — quality metrics exist and are recorded
4. preprocessing_documented — data preprocessing steps are recorded
5. bias_mitigation_documented — measures to detect/prevent biases [Art. 10(2)(g)]
6. data_gaps_identified — identification of data gaps [Art. 10(2)(h)]

Bias examination passes if: bias/fairness report exists, OR class balance data
is within the 60/40 threshold. Fails if: no bias analysis at all, or data
shows imbalance > 60/40. This avoids false-FAILing repos that have done bias
work but don't publish raw class statistics.
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral
from app.schemas.scanner import ScannerOutput, TrainingDataStats
from app.services.compliance.citations import ART_10

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
        bias_examined, imbalance_details = self._check_bias_examination(scanner_output, stats)
        quality = stats.quality_metrics_logged
        preprocessing = stats.preprocessing_documented
        bias_mitigation = scanner_output.has_bias_mitigation_docs
        data_gaps = scanner_output.has_data_gaps_identified

        sub_checks: dict[str, bool] = {
            "provenance_documented": provenance,
            "bias_examined": bias_examined,
            "data_quality_metrics_logged": quality,
            "preprocessing_documented": preprocessing,
            "bias_mitigation_documented": bias_mitigation,
            "data_gaps_identified": data_gaps,
        }

        passed = sum(1 for v in sub_checks.values() if v)
        total = len(sub_checks)

        if passed == total:
            status = "PASS"
        elif passed == 0:
            status = "FAIL"
        else:
            status = "PARTIAL"

        remediation = self._build_remediation(
            provenance, bias_examined, quality, preprocessing,
            bias_mitigation, data_gaps, imbalance_details,
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

    def _check_bias_examination(
        self, scanner_output: ScannerOutput, stats: TrainingDataStats
    ) -> tuple[bool, dict | None]:
        """Check if bias has been examined per Art 10.2(f-g).

        Pass if: bias/fairness report exists OR class balance data is within threshold.
        Fail if: no bias analysis found at all, or data shows imbalance > threshold.

        Returns (bias_examined, imbalance_details_or_none).
        """
        class_balance = stats.class_balance

        # If class balance data is provided, validate it
        if class_balance:
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
            # Class balance data exists and is within threshold
            return True, None

        # No class balance data — check if bias analysis files exist
        if scanner_output.has_data_documentation:
            return True, None

        return False, None

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "provenance_documented": f"no data provenance — {ART_10['provenance']}",
        "bias_examined": f"no bias analysis — {ART_10['bias']}",
        "data_quality_metrics_logged": f"no quality metrics — {ART_10['quality']}",
        "preprocessing_documented": f"no preprocessing docs — {ART_10['preprocessing']}",
        "bias_mitigation_documented": f"no bias mitigation measures — {ART_10['bias_mitigation']}",
        "data_gaps_identified": f"no data gaps analysis — {ART_10['data_gaps']}",
    }

    def _build_evidence_description(
        self, status: str, sub_checks: dict[str, bool]
    ) -> str:
        """Build a human-readable evidence description."""
        if status == "PASS":
            return (
                "Training data governance requirements satisfied:"
                " provenance documented, bias analysis conducted,"
                " quality metrics logged, preprocessing documented,"
                " bias mitigation measures in place, data gaps identified."
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
        bias_examined: bool,
        quality: bool,
        preprocessing: bool,
        bias_mitigation: bool,
        data_gaps: bool,
        imbalance_details: dict | None,
    ) -> str:
        """Build actionable remediation guidance."""
        actions = []

        if not provenance:
            actions.append(
                "Document training data sources, provenance chain,"
                " and collection methodology per Art. 10(2)(b)."
            )
        if not bias_examined:
            if imbalance_details:
                attr = imbalance_details["attribute"]
                ratio = imbalance_details["ratio"]
                actions.append(
                    f"Address {attr} class imbalance ({ratio})"
                    " through resampling or re-collection."
                )
            else:
                actions.append(
                    "Conduct and document a bias analysis examining protected"
                    " attributes for representativeness per Art. 10(2)(f-g)."
                )
        if not quality:
            actions.append(
                "Log data quality metrics (completeness, consistency, accuracy)"
                " per Art. 10(3)."
            )
        if not preprocessing:
            actions.append(
                "Document all data preprocessing and transformation steps"
                " per Art. 10(2)(e)."
            )
        if not bias_mitigation:
            actions.append(
                "Document measures to detect, prevent, and mitigate biases"
                " per Art. 10(2)(g)."
            )
        if not data_gaps:
            actions.append(
                "Identify and document relevant data gaps or shortcomings"
                " per Art. 10(2)(h)."
            )

        return " ".join(actions) if actions else ""
