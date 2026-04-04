"""Article 15 — Accuracy, Robustness, and Cybersecurity compliance check.

EU AI Act Article 15 requires high-risk AI systems to achieve an appropriate
level of accuracy, robustness, and cybersecurity.

Sub-checks:
1. test_metrics_logged — test set performance metrics are logged
2. adversarial_tested — adversarial robustness has been tested
3. versioning_in_place — model versioning exists for security/rollback
4. cybersecurity_measures — resilience against attacks [Art. 15(5)]
5. feedback_loop_prevention — eliminate/reduce biased feedback loops [Art. 15(4)]
6. error_resilience — resilient to errors, faults, inconsistencies [Art. 15(4)]
"""

from __future__ import annotations

from app.schemas.compliance import CheckEvidence, ComplianceCheck, SeverityLiteral, SubCheckDetail
from app.schemas.scanner import PerformanceMetrics, ScannerOutput
from app.services.compliance.citations import ART_15


class Article15Check:
    """Accuracy, Robustness, and Cybersecurity check per EU AI Act Article 15."""

    rule_id: str = "EU_AI_ART_15"
    rule_name: str = "Accuracy, Robustness, Cybersecurity"
    article: str = "Article 15"
    severity: SeverityLiteral = "high"

    _SUB_CHECK_META: dict[str, tuple[str, list[str], str]] = {
        "test_metrics_logged": (
            "Test set performance metrics logged",
            ["eval_results/*", "metrics/*", "benchmark/*"],
            ART_15["test_metrics"],
        ),
        "adversarial_tested": (
            "Adversarial robustness testing conducted",
            ["tests/*", "test/*"],
            ART_15["adversarial"],
        ),
        "versioning_in_place": (
            "Model versioning for rollback and change tracking",
            [".github/workflows/*", ".dvc/*"],
            ART_15["versioning"],
        ),
        "cybersecurity_measures": (
            "Cybersecurity measures against attacks documented",
            ["docs/security/*", "SECURITY.md"],
            ART_15["cybersecurity"],
        ),
        "feedback_loop_prevention": (
            "Measures to eliminate/reduce biased feedback loops",
            ["docs/monitoring/*", "docs/fairness/*"],
            ART_15["feedback_loop"],
        ),
        "error_resilience": (
            "Error resilience and fault tolerance documented",
            ["docs/reliability/*", "docs/safety/*"],
            ART_15["error_resilience"],
        ),
    }

    # Map sub-check IDs to scanner field names for matched_paths lookup.
    _SCANNER_FIELD_MAP: dict[str, str] = {
        "test_metrics_logged": "has_performance_metrics",
        "adversarial_tested": "has_adversarial_testing",
        "versioning_in_place": "has_versioning",
        "cybersecurity_measures": "has_cybersecurity_docs",
        "feedback_loop_prevention": "has_feedback_loop_prevention",
        "error_resilience": "has_error_resilience_docs",
    }

    def evaluate(self, scanner_output: ScannerOutput) -> ComplianceCheck:
        metrics = scanner_output.performance_metrics or PerformanceMetrics()

        test_metrics = self._check_test_metrics(metrics)
        adversarial = metrics.adversarial_tested
        versioning = scanner_output.has_versioning
        cybersecurity = scanner_output.has_cybersecurity_docs
        feedback_loop = scanner_output.has_feedback_loop_prevention
        error_resilience = scanner_output.has_error_resilience_docs

        sub_checks = {
            "test_metrics_logged": test_metrics,
            "adversarial_tested": adversarial,
            "versioning_in_place": versioning,
            "cybersecurity_measures": cybersecurity,
            "feedback_loop_prevention": feedback_loop,
            "error_resilience": error_resilience,
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
            "Article 15 requires high-risk AI systems to achieve appropriate levels"
            " of accuracy, robustness, and cybersecurity. This repository shows"
            f" {passed} of {total} accuracy/robustness signals, indicating "
            + ("full" if passed == total else "partial" if passed > 0 else "no")
            + " accuracy, robustness, and cybersecurity documentation."
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

    def _check_test_metrics(self, metrics: PerformanceMetrics) -> bool:
        """Test metrics logged if any standard metric has a value."""
        return any(
            v is not None
            for v in [
                metrics.accuracy,
                metrics.precision,
                metrics.recall,
                metrics.f1,
                metrics.auc,
            ]
        )

    _FAILURE_DESCRIPTIONS: dict[str, str] = {
        "test_metrics_logged": f"no test metrics — {ART_15['test_metrics']}",
        "adversarial_tested": f"no adversarial testing — {ART_15['adversarial']}",
        "versioning_in_place": f"no versioning — {ART_15['versioning']}",
        "cybersecurity_measures": f"no cybersecurity measures — {ART_15['cybersecurity']}",
        "feedback_loop_prevention": f"no feedback loop prevention — {ART_15['feedback_loop']}",
        "error_resilience": f"no error resilience — {ART_15['error_resilience']}",
    }

    def _describe(self, status: str, sub_checks: dict) -> str:
        if status == "PASS":
            return (
                "Accuracy, robustness, and cybersecurity requirements met:"
                " test metrics, adversarial testing, versioning, cybersecurity,"
                " feedback loop prevention, and error resilience in place."
            )
        failures = [
            self._FAILURE_DESCRIPTIONS.get(k, k.replace("_", " "))
            for k, v in sub_checks.items() if not v
        ]
        return f"Accuracy/robustness/cybersecurity gaps: {', '.join(failures)}."

    def _build_remediation(self, sub_checks: dict) -> str:
        actions = []
        if not sub_checks["test_metrics_logged"]:
            actions.append(
                "Log test set performance metrics"
                " (accuracy, precision, recall, F1) per Art. 15(2)."
            )
        if not sub_checks["adversarial_tested"]:
            actions.append(
                "Conduct adversarial robustness testing per Art. 15(5)."
            )
        if not sub_checks["versioning_in_place"]:
            actions.append(
                "Implement model versioning for rollback capability"
                " and change tracking per Art. 15(4)."
            )
        if not sub_checks["cybersecurity_measures"]:
            actions.append(
                "Document cybersecurity measures against data poisoning,"
                " model poisoning, and adversarial attacks per Art. 15(5)."
            )
        if not sub_checks["feedback_loop_prevention"]:
            actions.append(
                "Document measures to eliminate/reduce biased output"
                " feedback loops per Art. 15(4)."
            )
        if not sub_checks["error_resilience"]:
            actions.append(
                "Document error resilience, fault tolerance, and"
                " graceful degradation measures per Art. 15(4)."
            )
        return " ".join(actions)
