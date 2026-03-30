"""Evidence merger — overlay uploaded document evidence onto ScannerOutput.

When a user uploads external compliance documents (QMS, FRIA, conformity
certificates, etc.), this module maps them to the corresponding ScannerOutput
boolean signals so the compliance engine treats them as satisfied.

Pure function: takes a ScannerOutput + list of evidence items, returns
a new ScannerOutput with additional signals flipped.
"""

from __future__ import annotations

from app.schemas.scanner import ScannerOutput

# Map each document type to the ScannerOutput boolean fields it satisfies.
# When a document of this type is uploaded, these fields are set to True.
DOC_TYPE_SIGNAL_MAP: dict[str, list[str]] = {
    "qms": [
        "has_qms_docs",
        "has_contact_info",  # QMS docs include responsible person / contact
    ],
    "fria": [
        "has_impact_assessment",
        "has_risk_assessment",
    ],
    "conformity": [
        "has_conformity_assessment",
        "has_contact_info",  # Conformity declarations include provider contact
        "has_standards_applied",  # Conformity declarations list harmonised standards
    ],
    "monitoring_plan": [
        "has_monitoring_config",
        "has_logging_config",  # Monitoring plans encompass logging requirements
        "has_feedback_loop_prevention",  # Monitoring plans address feedback loops
        "has_input_data_recording",  # Monitoring plans define what data gets logged
    ],
    "incident_procedure": [
        "has_incident_reporting",
        "has_risk_event_logging",  # Incident procedures define risk event logging
    ],
    "risk_assessment": [
        "has_risk_assessment",
        "has_failure_modes_doc",
        "has_mitigation_plan",
        "has_residual_risk_evaluation",
        "has_testing_metrics_defined",  # Risk assessments define test acceptance criteria
        "has_cybersecurity_docs",  # Risk assessments cover cybersecurity threats
        "has_error_resilience_docs",  # Risk assessments cover error handling/resilience
    ],
    "data_governance": [
        "has_data_documentation",
        "has_bias_mitigation_docs",
        "has_data_gaps_identified",
        "has_group_performance_docs",  # Data governance covers disaggregated metrics
    ],
    "model_card": [
        "has_model_card",
        "has_architecture_docs",
        "has_capabilities_limitations",
        "has_development_process_docs",  # Model cards describe development process
        "has_versioning",  # Model cards include version history
    ],
    "human_oversight": [
        "has_human_oversight_docs",
        "has_override_mechanism",
        "has_escalation_docs",
        "has_automation_bias_docs",
        "has_stop_mechanism",
    ],
    "transparency": [
        "has_ai_disclosure",
        "has_user_instructions",
        "has_explainability",
        "has_provider_identification",
        "has_synthetic_content_marking",  # Transparency docs cover content marking
        "has_feature_importance_docs",  # Transparency docs explain model features
        "has_copyright_policy",  # Transparency covers IP/copyright disclosure
    ],
}

# Map doc_type to the EU AI Act articles it helps satisfy.
DOC_TYPE_ARTICLE_MAP: dict[str, list[str]] = {
    "qms": ["Article 16", "Article 17"],
    "fria": ["Article 27"],
    "conformity": ["Article 16"],
    "monitoring_plan": ["Article 72", "Article 16"],
    "incident_procedure": ["Article 17"],
    "risk_assessment": ["Article 9"],
    "data_governance": ["Article 10"],
    "model_card": ["Article 11", "Article 53"],
    "human_oversight": ["Article 14", "Article 26"],
    "transparency": ["Article 13", "Article 50"],
}


class EvidenceItem:
    """A single uploaded evidence document with analysis results."""

    def __init__(
        self,
        evidence_id: str,
        doc_type: str,
        filename: str,
        description: str = "",
        keyword_matches: list[str] | None = None,
        llm_analysis: dict | None = None,
    ) -> None:
        self.evidence_id = evidence_id
        self.doc_type = doc_type
        self.filename = filename
        self.description = description
        self.keyword_matches = keyword_matches or []
        self.llm_analysis = llm_analysis

    @property
    def signals(self) -> list[str]:
        """Scanner signals this evidence satisfies."""
        return DOC_TYPE_SIGNAL_MAP.get(self.doc_type, [])

    @property
    def articles(self) -> list[str]:
        """EU AI Act articles this evidence helps satisfy."""
        return DOC_TYPE_ARTICLE_MAP.get(self.doc_type, [])


def merge_evidence(
    scanner_output: ScannerOutput,
    evidence_items: list[EvidenceItem],
) -> ScannerOutput:
    """Overlay uploaded evidence signals onto a ScannerOutput.

    Creates a copy of the scanner output with additional boolean fields
    flipped to True based on the uploaded evidence types. Also adds
    evidence file references to matched_paths.

    Args:
        scanner_output: Base scanner output (from repo scan or empty).
        evidence_items: List of uploaded and analyzed evidence documents.

    Returns:
        New ScannerOutput with evidence merged in.
    """
    if not evidence_items:
        return scanner_output

    # Build dict of fields to update
    updates: dict[str, bool] = {}
    path_updates: dict[str, list[str]] = {}

    for item in evidence_items:
        for signal in item.signals:
            updates[signal] = True
            path_updates.setdefault(signal, []).append(
                f"[Uploaded] {item.filename}"
            )

    # Create updated output (immutable pattern — new object)
    data = scanner_output.model_dump()

    # Flip boolean fields
    for field, value in updates.items():
        if field in data:
            data[field] = value

    # Merge matched_paths
    existing_paths = data.get("matched_paths", {})
    for field, paths in path_updates.items():
        existing = existing_paths.get(field, [])
        existing_paths[field] = existing + [p for p in paths if p not in existing]
    data["matched_paths"] = existing_paths

    # Special handling: FRIA upload injects a synthetic detected domain
    # so Art. 27 affected_categories_identified check can pass
    fria_items = [item for item in evidence_items if item.doc_type == "fria"]
    if fria_items:
        from app.schemas.scanner import DetectedDomain
        existing_domains = data.get("detected_domains", [])
        # Only add if no domains already detected
        if not existing_domains:
            data["detected_domains"] = [
                DetectedDomain(
                    domain="fria_documented",
                    annex_iii_category="4a",
                    confidence=0.8,
                    matched_keywords=["fundamental rights impact assessment uploaded"],
                ).model_dump(),
            ]

    return ScannerOutput(**data)


def create_empty_scanner_output(repo_url: str = "deployer://no-repo") -> ScannerOutput:
    """Create a minimal ScannerOutput for deployer-only scans (no repo)."""
    return ScannerOutput(repo_url=repo_url)
