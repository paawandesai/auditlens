"""Tests for content_analyzer — pure logic, no HTTP."""

from __future__ import annotations

from app.scanners.content_analyzer import check_file_tree_flags, extract_content_flags


class TestCheckFileTreeFlags:
    """Tests for file-tree pattern matching."""

    def test_empty_tree_all_false(self):
        flags = check_file_tree_flags([])
        assert flags.get("has_model_card") is not True
        assert flags.get("has_risk_assessment") is not True
        assert flags.get("has_test_suite") is not True

    def test_model_card_detected(self):
        flags = check_file_tree_flags(["MODEL_CARD.md"])
        assert flags["has_model_card"] is True

    def test_model_card_case_insensitive(self):
        flags = check_file_tree_flags(["model_card.md"])
        assert flags["has_model_card"] is True

    def test_model_card_nested(self):
        flags = check_file_tree_flags(["docs/model_card.md"])
        assert flags["has_model_card"] is True

    def test_risk_assessment_variations(self):
        for path in ["RISK_ASSESSMENT.md", "risk_assessment.txt", "risk-assessment.md",
                      "risk_management.md", "risk-management-plan.md"]:
            flags = check_file_tree_flags([path])
            assert flags["has_risk_assessment"] is True, f"Failed for {path}"

    def test_architecture_docs(self):
        flags = check_file_tree_flags(["ARCHITECTURE.md"])
        assert flags["has_architecture_docs"] is True

    def test_architecture_docs_nested(self):
        flags = check_file_tree_flags(["docs/design-overview.md"])
        assert flags["has_architecture_docs"] is True

    def test_tests_directory(self):
        flags = check_file_tree_flags(["tests/test_model.py"])
        assert flags["has_test_suite"] is True

    def test_test_directory_alt(self):
        flags = check_file_tree_flags(["test/unit_test.py"])
        assert flags["has_test_suite"] is True

    def test_github_workflows_versioning(self):
        flags = check_file_tree_flags([".github/workflows/ci.yml"])
        assert flags["has_versioning"] is True

    def test_dvc_versioning(self):
        flags = check_file_tree_flags([".dvc/config"])
        assert flags["has_versioning"] is True

    def test_data_card_detected(self):
        flags = check_file_tree_flags(["data_card.md"])
        assert flags["has_data_documentation"] is True

    def test_dataset_card_detected(self):
        flags = check_file_tree_flags(["dataset_card.yaml"])
        assert flags["has_data_documentation"] is True

    def test_datasheet_detected(self):
        flags = check_file_tree_flags(["datasheet.md"])
        assert flags["has_data_documentation"] is True

    def test_failure_modes_risk_tests(self):
        flags = check_file_tree_flags(["tests/risk_assessment_test.py"])
        assert flags["has_failure_modes_doc"] is True

    def test_failure_modes_safety_tests(self):
        flags = check_file_tree_flags(["tests/safety_checks.py"])
        assert flags["has_failure_modes_doc"] is True

    def test_retention_policy(self):
        flags = check_file_tree_flags(["RETENTION_POLICY.md"])
        assert flags["has_logging_config"] is True

    def test_data_retention(self):
        flags = check_file_tree_flags(["data_retention_policy.md"])
        assert flags["has_logging_config"] is True

    def test_metrics_files_detected(self):
        flags = check_file_tree_flags(["eval_results.json"])
        assert flags["performance_metrics_present"] is True

    def test_benchmark_files_detected(self):
        flags = check_file_tree_flags(["benchmark_scores.csv"])
        assert flags["performance_metrics_present"] is True

    def test_bias_report_detected(self):
        flags = check_file_tree_flags(["bias_report.md"])
        assert flags["bias_analysis_found"] is True

    def test_fairness_report_detected(self):
        flags = check_file_tree_flags(["fairness_report.pdf"])
        assert flags["bias_analysis_found"] is True

    def test_user_instructions_detected(self):
        flags = check_file_tree_flags(["user_guide.md"])
        assert flags["user_instructions_found"] is True

    def test_deployer_guide_detected(self):
        flags = check_file_tree_flags(["deployer_guide.md"])
        assert flags["user_instructions_found"] is True

    def test_combined_real_repo_tree(self):
        """Simulate a well-documented repo."""
        paths = [
            "README.md",
            "MODEL_CARD.md",
            "RISK_ASSESSMENT.md",
            "docs/architecture.md",
            "tests/test_model.py",
            "tests/safety_test.py",
            ".github/workflows/ci.yml",
            "requirements.txt",
            "data_card.yaml",
            "eval_results.json",
            "bias_report.md",
        ]
        flags = check_file_tree_flags(paths)
        assert flags["has_model_card"] is True
        assert flags["has_risk_assessment"] is True
        assert flags["has_architecture_docs"] is True
        assert flags["has_test_suite"] is True
        assert flags["has_versioning"] is True
        assert flags["has_data_documentation"] is True
        assert flags["has_failure_modes_doc"] is True
        assert flags["performance_metrics_present"] is True
        assert flags["bias_analysis_found"] is True


class TestExtractContentFlags:
    """Tests for content keyword matching."""

    def test_empty_content_all_false(self):
        flags = extract_content_flags({})
        assert flags.get("has_human_oversight_docs") is not True
        assert flags.get("has_explainability") is not True

    def test_human_review_detected(self):
        flags = extract_content_flags({"README.md": "We include human review steps"})
        assert flags["has_human_oversight_docs"] is True

    def test_manual_review_detected(self):
        flags = extract_content_flags({"doc.md": "manual review of predictions"})
        assert flags["has_human_oversight_docs"] is True

    def test_human_in_the_loop(self):
        flags = extract_content_flags({"doc.md": "Uses a human-in-the-loop approach"})
        assert flags["has_human_oversight_docs"] is True

    def test_override_detected(self):
        flags = extract_content_flags({"doc.md": "Admin can override model decisions"})
        assert flags["has_override_mechanism"] is True

    def test_kill_switch_detected(self):
        flags = extract_content_flags({"doc.md": "Emergency kill_switch for model"})
        assert flags["has_override_mechanism"] is True

    def test_feature_importance_detected(self):
        flags = extract_content_flags({"doc.md": "We log feature importance scores"})
        assert flags["has_feature_importance_docs"] is True

    def test_shap_explainability(self):
        flags = extract_content_flags({"README.md": "We use SHAP values for explainability"})
        assert flags["has_explainability"] is True

    def test_lime_explainability(self):
        flags = extract_content_flags({"README.md": "LIME is used for local explanations"})
        assert flags["has_explainability"] is True

    def test_explainability_substring(self):
        flags = extract_content_flags({"README.md": "Model explainability documentation"})
        assert flags["has_explainability"] is True

    def test_logging_signals(self):
        flags = extract_content_flags({"doc.md": "We configure audit logging for all decisions"})
        assert flags["has_logging_config"] is True

    def test_telemetry_signal(self):
        flags = extract_content_flags({"doc.md": "Telemetry is enabled for monitoring"})
        assert flags["has_logging_config"] is True

    def test_monitoring_mitigation(self):
        flags = extract_content_flags({"doc.md": "We have monitoring dashboards for drift"})
        assert flags["has_mitigation_plan"] is True

    def test_drift_mitigation(self):
        flags = extract_content_flags({"doc.md": "Drift detection alerts are configured"})
        assert flags["has_mitigation_plan"] is True

    def test_adversarial_testing(self):
        flags = extract_content_flags({"doc.md": "We run adversarial attacks against the model"})
        assert flags["adversarial_tested"] is True

    def test_robustness_test(self):
        flags = extract_content_flags({"doc.md": "Robustness test suite included"})
        assert flags["adversarial_tested"] is True

    def test_training_data_provenance(self):
        flags = extract_content_flags({"doc.md": "Data source: internal HR database"})
        training_sub = flags["training_data_sub"]
        assert training_sub["provenance_documented"] is True

    def test_training_data_preprocessing(self):
        flags = extract_content_flags({"doc.md": "Preprocessing pipeline removes PII"})
        training_sub = flags["training_data_sub"]
        assert training_sub["preprocessing_documented"] is True

    def test_feature_engineering_preprocessing(self):
        flags = extract_content_flags({"doc.md": "Feature engineering steps documented"})
        training_sub = flags["training_data_sub"]
        assert training_sub["preprocessing_documented"] is True

    def test_case_insensitive(self):
        flags = extract_content_flags({"doc.md": "SHAP values for Feature Importance"})
        assert flags["has_explainability"] is True
        assert flags["has_feature_importance_docs"] is True

    def test_combined_signals(self):
        content = {
            "README.md": (
                "This model uses SHAP for explainability. "
                "Human review is required for all decisions. "
                "Override mechanism is available via admin panel. "
                "We run adversarial testing and monitor for drift. "
                "Data source is documented. Preprocessing steps are logged."
            )
        }
        flags = extract_content_flags(content)
        assert flags["has_explainability"] is True
        assert flags["has_human_oversight_docs"] is True
        assert flags["has_override_mechanism"] is True
        assert flags["adversarial_tested"] is True
        assert flags["has_mitigation_plan"] is True
        training_sub = flags["training_data_sub"]
        assert training_sub["provenance_documented"] is True
        assert training_sub["preprocessing_documented"] is True
