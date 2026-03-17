"""Scanner output models — what the scanning pipeline produces.

These models represent the combined output of Pass 1 (dependency detection)
and Pass 2 (AST analysis). They serve as input to the compliance engine.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DetectedFramework(BaseModel):
    """A detected ML/AI framework from dependency scanning (Pass 1)."""

    name: str
    version: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    hr_relevance_score: float = Field(ge=0.0, le=1.0)


class CodeSignal(BaseModel):
    """A code pattern detected by AST analysis (Pass 2)."""

    signal_type: Literal["variable", "function", "class", "string", "comment"]
    name: str
    context: str
    hr_relevance_score: float = Field(ge=0.0, le=1.0)


class TrainingDataStats(BaseModel):
    """Structured training data statistics from scanner analysis."""

    provenance_documented: bool = False
    quality_metrics_logged: bool = False
    preprocessing_documented: bool = False
    class_balance: dict[str, dict[str, float]] | None = None


class PerformanceMetrics(BaseModel):
    """Structured model performance metrics from scanner analysis."""

    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    auc: float | None = None
    adversarial_tested: bool = False


class ScannerOutput(BaseModel):
    """Combined output from all scanning passes. Input to the compliance engine."""

    repo_url: str
    detected_frameworks: list[DetectedFramework] = Field(default_factory=list)
    code_signals: list[CodeSignal] = Field(default_factory=list)

    # Metadata flags the scanner may discover in the repo
    has_model_card: bool = False
    has_risk_assessment: bool = False
    has_data_documentation: bool = False
    has_explainability: bool = False
    has_human_oversight_docs: bool = False
    has_logging_config: bool = False
    has_versioning: bool = False
    has_test_suite: bool = False

    # Distinct flags for sub-checks that were previously aliased
    has_architecture_docs: bool = False
    has_feature_importance_docs: bool = False
    has_override_mechanism: bool = False
    has_escalation_docs: bool = False
    has_failure_modes_doc: bool = False
    has_mitigation_plan: bool = False

    # Typed structured data from scanner analysis
    training_data_stats: TrainingDataStats | None = None
    performance_metrics: PerformanceMetrics | None = None
