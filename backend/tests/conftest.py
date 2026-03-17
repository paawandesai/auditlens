"""Shared test fixtures for compliance engine tests."""

from __future__ import annotations

import pytest

from app.schemas.scanner import (
    CodeSignal,
    DetectedFramework,
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
