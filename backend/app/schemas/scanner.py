"""Scanner output models — what the scanning pipeline produces.

These models represent the combined output of all scanning passes
(dependency detection, import scanning, config scanning, content analysis).
They serve as input to the compliance engine.
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


class DetectedDomain(BaseModel):
    """An Annex III domain detected from content keyword analysis."""

    domain: str
    annex_iii_category: str
    confidence: float = Field(ge=0.0, le=1.0)
    matched_keywords: list[str]


class ConfigSignal(BaseModel):
    """An AI usage signal detected from configuration files."""

    source: Literal["env", "docker", "terraform"]
    framework_hint: str
    detail: str
    confidence: float = Field(ge=0.0, le=1.0)


class DocValidation(BaseModel):
    """Validation result for a compliance document's section completeness."""

    doc_type: str
    sections_found: list[str]
    sections_missing: list[str]
    completeness_score: float = Field(ge=0.0, le=1.0)


class CodeSignal(BaseModel):
    """A code pattern detected by AST analysis (Pass 2)."""

    signal_type: Literal["variable", "function", "class", "string", "comment"]
    name: str
    context: str
    hr_relevance_score: float = Field(ge=0.0, le=1.0)


class DetectedImport(BaseModel):
    """An import detected by AST analysis with file + line location."""

    module: str
    package: str | None = None
    framework: str | None = None
    file: str = ""
    line: int = 0
    col: int = 0
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    hr_relevance_score: float = Field(ge=0.0, le=1.0, default=0.0)


class CallChainFinding(BaseModel):
    """A regulated decision pattern detected via AST call-chain analysis."""

    pattern: Literal[
        "conditional_branching",
        "database_persistence",
        "ui_rendering",
        "downstream_api_call",
    ]
    ai_call_file: str
    ai_call_line: int
    ai_framework: str
    decision_file: str
    decision_line: int
    decision_context: str = ""
    severity: Literal["critical", "warning", "info"] = "warning"


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


class RiskClassification(BaseModel):
    """Risk classification result from three-signal scoring."""

    risk_level: Literal["UNACCEPTABLE", "HIGH", "LIMITED", "MINIMAL", "UNDETERMINED"]
    risk_score: int = Field(ge=0, le=100)
    annex_iii_category: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[dict] = Field(default_factory=list)


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
    has_user_instructions: bool = False

    # Phase 3 — new sub-check fields (all default False for backward compat)
    # Article 9
    has_residual_risk_evaluation: bool = False
    has_testing_metrics_defined: bool = False
    # Article 10
    has_bias_mitigation_docs: bool = False
    has_data_gaps_identified: bool = False
    # Article 11
    has_development_process_docs: bool = False
    has_standards_applied: bool = False
    # Article 12
    has_risk_event_logging: bool = False
    has_input_data_recording: bool = False
    # Article 13
    has_capabilities_limitations: bool = False
    has_group_performance_docs: bool = False
    # Article 14
    has_automation_bias_docs: bool = False
    has_stop_mechanism: bool = False
    # Article 15
    has_cybersecurity_docs: bool = False
    has_feedback_loop_prevention: bool = False
    has_error_resilience_docs: bool = False

    # Articles 16, 17, 26, 27, 53, 55, 72 — organizational/GPAI signals
    has_contact_info: bool = False
    has_impact_assessment: bool = False
    has_monitoring_config: bool = False
    has_incident_reporting: bool = False
    has_copyright_policy: bool = False
    has_qms_docs: bool = False
    has_conformity_assessment: bool = False

    # Article 5 — prohibited practice indicators (absence = PASS)
    has_social_scoring_indicators: bool = False
    has_biometric_identification: bool = False
    has_emotion_inference: bool = False

    # Article 50 — transparency obligations (presence = PASS)
    has_ai_disclosure: bool = False
    has_synthetic_content_marking: bool = False
    has_provider_identification: bool = False

    # Typed structured data from scanner analysis
    training_data_stats: TrainingDataStats | None = None
    performance_metrics: PerformanceMetrics | None = None

    # Enhanced scanning signals (ported from Systima Comply, Apache 2.0)
    detected_domains: list[DetectedDomain] = Field(default_factory=list)
    config_signals: list[ConfigSignal] = Field(default_factory=list)
    doc_validations: list[DocValidation] = Field(default_factory=list)

    # AST-based import detection with file+line precision
    detected_imports: list[DetectedImport] = Field(default_factory=list)

    # Call-chain analysis findings (AI output → decision patterns)
    call_chain_findings: list[CallChainFinding] = Field(default_factory=list)

    # Matched file paths per signal (populated by scanner, used by article checks)
    matched_paths: dict[str, list[str]] = Field(default_factory=dict)

    # External evidence from uploaded documents
    external_evidence: list[dict] = Field(default_factory=list)

    # Risk classification (computed after all scan passes)
    risk_classification: RiskClassification | None = None
