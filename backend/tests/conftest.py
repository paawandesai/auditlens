"""Shared test fixtures for compliance engine tests."""

from __future__ import annotations

import os

import pytest

# Disable auth for all tests by default (individual tests can re-enable)
os.environ.setdefault("AUDITLENS_AUTH_ENABLED", "false")


def pytest_addoption(parser):
    parser.addoption(
        "--run-golden", action="store_true", default=False,
        help="Run golden repo tests (hits live GitHub API)",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-golden"):
        skip = pytest.mark.skip(reason="Need --run-golden to run")
        for item in items:
            if "golden" in item.keywords:
                item.add_marker(skip)

from app.schemas.scanner import (
    CallChainFinding,
    CodeSignal,
    DetectedFramework,
    DetectedImport,
    PerformanceMetrics,
    ScannerOutput,
    TrainingDataStats,
)


@pytest.fixture
def minimal_scanner_output() -> ScannerOutput:
    """Bare-minimum scanner output — no frameworks, no signals, no metadata."""
    return ScannerOutput(repo_url="https://github.com/example/empty-repo")


@pytest.fixture
def fully_compliant_scanner_output() -> ScannerOutput:
    """Scanner output for a well-documented, compliant AI system."""
    return ScannerOutput(
        repo_url="https://github.com/example/compliant-hr-ai",
        detected_frameworks=[
            DetectedFramework(
                name="scikit-learn",
                version="1.4.0",
                confidence=0.95,
                hr_relevance_score=0.6,
            ),
        ],
        code_signals=[
            CodeSignal(
                signal_type="function",
                name="screen_candidates",
                context="def screen_candidates(applications): ...",
                hr_relevance_score=0.9,
            ),
        ],
        has_model_card=True,
        has_risk_assessment=True,
        has_data_documentation=True,
        has_explainability=True,
        has_human_oversight_docs=True,
        has_logging_config=True,
        has_versioning=True,
        has_test_suite=True,
        # Distinct flags for sub-checks
        has_architecture_docs=True,
        has_feature_importance_docs=True,
        has_override_mechanism=True,
        has_escalation_docs=True,
        has_failure_modes_doc=True,
        has_mitigation_plan=True,
        has_user_instructions=True,
        # Article 5 — no prohibited indicators (all False = good)
        has_social_scoring_indicators=False,
        has_biometric_identification=False,
        has_emotion_inference=False,
        # Article 50 — transparency present (all True = good)
        has_ai_disclosure=True,
        has_synthetic_content_marking=True,
        has_provider_identification=True,
        # Phase 3 new fields — all True for fully compliant
        has_residual_risk_evaluation=True,
        has_testing_metrics_defined=True,
        has_bias_mitigation_docs=True,
        has_data_gaps_identified=True,
        has_development_process_docs=True,
        has_standards_applied=True,
        has_risk_event_logging=True,
        has_input_data_recording=True,
        has_capabilities_limitations=True,
        has_group_performance_docs=True,
        has_automation_bias_docs=True,
        has_stop_mechanism=True,
        has_cybersecurity_docs=True,
        has_feedback_loop_prevention=True,
        has_error_resilience_docs=True,
        training_data_stats=TrainingDataStats(
            provenance_documented=True,
            class_balance={"gender": {"male": 52, "female": 48}},
            quality_metrics_logged=True,
            preprocessing_documented=True,
        ),
        performance_metrics=PerformanceMetrics(
            accuracy=0.92,
            precision=0.89,
            recall=0.91,
            f1=0.90,
            adversarial_tested=True,
        ),
    )


@pytest.fixture
def non_compliant_scanner_output() -> ScannerOutput:
    """Scanner output for a poorly documented AI system — should fail most checks."""
    return ScannerOutput(
        repo_url="https://github.com/example/bad-hr-ai",
        detected_frameworks=[
            DetectedFramework(
                name="tensorflow",
                version="2.15.0",
                confidence=0.99,
                hr_relevance_score=0.5,
            ),
        ],
        code_signals=[
            CodeSignal(
                signal_type="variable",
                name="candidate_score",
                context="candidate_score = model.predict(features)",
                hr_relevance_score=0.85,
            ),
        ],
        has_model_card=False,
        has_risk_assessment=False,
        has_data_documentation=False,
        has_explainability=False,
        has_human_oversight_docs=False,
        has_logging_config=False,
        has_versioning=False,
        has_test_suite=False,
        training_data_stats=None,
        performance_metrics=None,
    )


@pytest.fixture
def prohibited_scanner_output() -> ScannerOutput:
    """Scanner output with prohibited AI practice indicators — should fail Art. 5."""
    return ScannerOutput(
        repo_url="https://github.com/example/prohibited-ai",
        has_social_scoring_indicators=True,
        has_biometric_identification=True,
        has_emotion_inference=True,
        has_ai_disclosure=False,
        has_synthetic_content_marking=False,
        has_provider_identification=False,
    )


@pytest.fixture
def partial_scanner_output() -> ScannerOutput:
    """Scanner output with some documentation but gaps — should trigger PARTIAL."""
    return ScannerOutput(
        repo_url="https://github.com/example/partial-hr-ai",
        detected_frameworks=[
            DetectedFramework(
                name="pytorch",
                version="2.2.0",
                confidence=0.90,
                hr_relevance_score=0.5,
            ),
        ],
        code_signals=[],
        has_model_card=True,
        has_risk_assessment=True,
        has_data_documentation=True,
        has_explainability=False,
        has_human_oversight_docs=True,
        has_logging_config=True,
        has_versioning=True,
        has_test_suite=False,
        # Partial distinct flags
        has_architecture_docs=True,
        has_feature_importance_docs=False,
        has_override_mechanism=True,
        has_escalation_docs=False,
        has_failure_modes_doc=True,
        has_mitigation_plan=False,
        # Phase 3 new fields — mixed for partial
        has_residual_risk_evaluation=True,
        has_testing_metrics_defined=False,
        has_bias_mitigation_docs=False,
        has_data_gaps_identified=True,
        has_development_process_docs=True,
        has_standards_applied=False,
        has_risk_event_logging=False,
        has_input_data_recording=True,
        has_capabilities_limitations=True,
        has_group_performance_docs=False,
        has_automation_bias_docs=False,
        has_stop_mechanism=True,
        has_cybersecurity_docs=False,
        has_feedback_loop_prevention=False,
        has_error_resilience_docs=True,
        training_data_stats=TrainingDataStats(
            provenance_documented=True,
            class_balance={"gender": {"male": 70, "female": 30}},
            quality_metrics_logged=True,
            preprocessing_documented=False,
        ),
        performance_metrics=PerformanceMetrics(
            accuracy=0.85,
            adversarial_tested=False,
        ),
    )
