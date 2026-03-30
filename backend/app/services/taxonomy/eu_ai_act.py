"""EU AI Act — complete article taxonomy for all company-facing obligations.

Maps all ~30 articles that companies must comply with, categorized by
assessment method:
- automated: Scanner can check this from code/repo analysis
- questionnaire: Requires self-assessment responses from the company
- document: Requires document upload and review

Articles 1-4 (scope/definitions), 18-25 (notified bodies), 40-49 (standards),
51-69 (governance) are regulatory infrastructure — not company obligations.
They are excluded from this taxonomy.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CheckType = Literal["automated", "questionnaire", "document"]
CoverageStatus = Literal["full", "partial", "planned", "not_applicable"]


class ArticleRequirement(BaseModel):
    """A specific requirement within an EU AI Act article."""

    requirement_id: str
    description: str
    check_type: CheckType
    scanner_fields: list[str]  # ScannerOutput fields that map to this requirement
    covered: bool  # Whether AuditLens currently checks this


class ArticleTaxonomy(BaseModel):
    """Complete taxonomy entry for one EU AI Act article."""

    article: str  # e.g., "Article 5"
    title: str
    summary: str
    risk_tier: str  # "all", "high_risk", "limited_risk", "general_purpose"
    severity: str  # "critical", "high", "medium", "low"
    check_type: CheckType  # Primary assessment method
    coverage: CoverageStatus
    requirements: list[ArticleRequirement]
    enforcement_date: str
    penalty_reference: str


# ---------------------------------------------------------------------------
# Complete EU AI Act taxonomy — all company-facing articles
# ---------------------------------------------------------------------------

EU_AI_ACT_TAXONOMY: list[ArticleTaxonomy] = [
    # ===== CHAPTER II: PROHIBITED PRACTICES =====
    ArticleTaxonomy(
        article="Article 5",
        title="Prohibited AI Practices",
        summary="Bans AI systems that pose unacceptable risks: social scoring, real-time biometric identification, emotion inference in workplaces/education, and manipulative/exploitative techniques.",
        risk_tier="all",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART5_1a",
                description="No subliminal or manipulative techniques",
                check_type="automated",
                scanner_fields=[],
                covered=False,
            ),
            ArticleRequirement(
                requirement_id="ART5_1b",
                description="No exploitation of vulnerabilities (age, disability, social situation)",
                check_type="questionnaire",
                scanner_fields=[],
                covered=False,
            ),
            ArticleRequirement(
                requirement_id="ART5_1c",
                description="No social scoring by public authorities",
                check_type="automated",
                scanner_fields=["has_social_scoring_indicators"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART5_1d",
                description="No real-time remote biometric identification in public spaces",
                check_type="automated",
                scanner_fields=["has_biometric_identification"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART5_1e",
                description="No emotion inference in workplace or education",
                check_type="automated",
                scanner_fields=["has_emotion_inference"],
                covered=True,
            ),
        ],
        enforcement_date="2025-02-02",
        penalty_reference="Up to 35M EUR or 7% of global annual turnover",
    ),

    # ===== CHAPTER II: CLASSIFICATION =====
    ArticleTaxonomy(
        article="Article 6",
        title="Classification Rules for High-Risk AI",
        summary="Defines when an AI system is classified as high-risk: Annex III listed use cases or safety component of products covered by EU harmonisation legislation.",
        risk_tier="all",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART6_2",
                description="Determine if AI falls under Annex III high-risk categories",
                check_type="automated",
                scanner_fields=["detected_domains", "risk_classification"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART6_1",
                description="Determine if AI is a safety component of a product under Annex I legislation",
                check_type="automated",
                scanner_fields=["has_risk_assessment"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART6_3",
                description="Risk level classification determined for the system",
                check_type="automated",
                scanner_fields=["risk_classification"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),

    # ===== CHAPTER III, SECTION 2: HIGH-RISK REQUIREMENTS =====
    ArticleTaxonomy(
        article="Article 8",
        title="Compliance with Requirements",
        summary="Meta-article requiring high-risk AI providers to ensure compliance with Articles 9-15, considering the intended purpose and the generally acknowledged state of the art.",
        risk_tier="high_risk",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART8_1",
                description="System designed and developed to comply with Art. 9-15",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART8_2",
                description="Intended purpose taken into account in design",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 9",
        title="Risk Management System",
        summary="Establish, implement, document and maintain a risk management system throughout the AI system's lifecycle. Identify risks, estimate likelihood and severity, adopt mitigation measures, and test.",
        risk_tier="high_risk",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART9_2a",
                description="Identify and analyse known and foreseeable risks",
                check_type="automated",
                scanner_fields=["has_risk_assessment"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART9_2b",
                description="Estimate risks under conditions of foreseeable misuse",
                check_type="automated",
                scanner_fields=["has_failure_modes_doc"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART9_2d",
                description="Adopt targeted risk management measures",
                check_type="automated",
                scanner_fields=["has_mitigation_plan"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART9_5",
                description="Evaluate residual risks after mitigation",
                check_type="automated",
                scanner_fields=["has_residual_risk_evaluation"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART9_6",
                description="Test against prior-defined metrics",
                check_type="automated",
                scanner_fields=["has_testing_metrics_defined"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 10",
        title="Data and Data Governance",
        summary="Training, validation and testing datasets shall meet quality criteria. Data provenance, bias examination, and preprocessing must be documented.",
        risk_tier="high_risk",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART10_2b",
                description="Document data provenance and collection methodology",
                check_type="automated",
                scanner_fields=["has_data_documentation", "training_data_stats"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART10_2e",
                description="Document preprocessing operations",
                check_type="automated",
                scanner_fields=["training_data_stats"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART10_2f",
                description="Examine for possible biases",
                check_type="automated",
                scanner_fields=["has_data_documentation", "training_data_stats"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART10_2g",
                description="Measures to detect, prevent, mitigate biases",
                check_type="automated",
                scanner_fields=["has_bias_mitigation_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART10_2h",
                description="Identify data gaps or shortcomings",
                check_type="automated",
                scanner_fields=["has_data_gaps_identified"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART10_3",
                description="Data quality criteria: relevance, representativeness, completeness",
                check_type="automated",
                scanner_fields=["training_data_stats"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 11",
        title="Technical Documentation",
        summary="Draw up technical documentation before placing on market. Must cover system design, development, capabilities, limitations, and conformity assessment process.",
        risk_tier="high_risk",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART11_1",
                description="Technical documentation per Annex IV (model card)",
                check_type="automated",
                scanner_fields=["has_model_card"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART11_ARCH",
                description="Architecture and design documentation",
                check_type="automated",
                scanner_fields=["has_architecture_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART11_PERF",
                description="Performance metrics recorded",
                check_type="automated",
                scanner_fields=["performance_metrics"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART11_DEV",
                description="Development process documentation",
                check_type="automated",
                scanner_fields=["has_development_process_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART11_STD",
                description="Standards applied documented",
                check_type="automated",
                scanner_fields=["has_standards_applied"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 12",
        title="Record-Keeping",
        summary="High-risk AI systems shall allow automatic recording of events (logs) for traceability throughout the system's lifecycle.",
        risk_tier="high_risk",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART12_1",
                description="Automatic recording of events (logging)",
                check_type="automated",
                scanner_fields=["has_logging_config"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART12_VER",
                description="Model versioning for traceability",
                check_type="automated",
                scanner_fields=["has_versioning"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART12_2a",
                description="Risk situation logging",
                check_type="automated",
                scanner_fields=["has_risk_event_logging"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART12_3c",
                description="Input data recording",
                check_type="automated",
                scanner_fields=["has_input_data_recording"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 13",
        title="Transparency and Provision of Information",
        summary="High-risk AI systems shall be designed to enable deployers to interpret output and use the system appropriately.",
        risk_tier="high_risk",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART13_3d",
                description="Explainability tools available",
                check_type="automated",
                scanner_fields=["has_explainability"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART13_3b_iv",
                description="Feature importance documented",
                check_type="automated",
                scanner_fields=["has_feature_importance_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART13_3",
                description="Instructions for use provided to deployers",
                check_type="automated",
                scanner_fields=["has_user_instructions", "has_model_card"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART13_3b",
                description="Capabilities and limitations stated",
                check_type="automated",
                scanner_fields=["has_capabilities_limitations"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART13_3b_v",
                description="Performance for specific groups documented",
                check_type="automated",
                scanner_fields=["has_group_performance_docs"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 14",
        title="Human Oversight",
        summary="High-risk AI systems shall be designed to allow effective human oversight during use, including ability to override, interpret, and stop the system.",
        risk_tier="high_risk",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART14_1",
                description="Human-in-the-loop mechanisms documented",
                check_type="automated",
                scanner_fields=["has_human_oversight_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART14_4d",
                description="Override or reverse capability",
                check_type="automated",
                scanner_fields=["has_override_mechanism"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART14_4c",
                description="Escalation procedures documented",
                check_type="automated",
                scanner_fields=["has_escalation_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART14_4b",
                description="Automation bias awareness",
                check_type="automated",
                scanner_fields=["has_automation_bias_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART14_4e",
                description="Stop mechanism (emergency halt)",
                check_type="automated",
                scanner_fields=["has_stop_mechanism"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 15",
        title="Accuracy, Robustness and Cybersecurity",
        summary="High-risk AI systems shall achieve appropriate levels of accuracy, robustness, and cybersecurity throughout their lifecycle.",
        risk_tier="high_risk",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART15_2",
                description="Accuracy metrics logged",
                check_type="automated",
                scanner_fields=["performance_metrics"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART15_5_ADV",
                description="Adversarial robustness testing",
                check_type="automated",
                scanner_fields=["performance_metrics"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART15_VER",
                description="Versioning in place",
                check_type="automated",
                scanner_fields=["has_versioning"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART15_5_SEC",
                description="Cybersecurity measures documented",
                check_type="automated",
                scanner_fields=["has_cybersecurity_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART15_4_FB",
                description="Feedback loop prevention",
                check_type="automated",
                scanner_fields=["has_feedback_loop_prevention"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART15_4_ERR",
                description="Error resilience documented",
                check_type="automated",
                scanner_fields=["has_error_resilience_docs"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),

    # ===== CHAPTER III, SECTION 3: PROVIDER OBLIGATIONS =====
    ArticleTaxonomy(
        article="Article 16",
        title="Obligations of Providers",
        summary="Providers of high-risk AI shall ensure compliance with Chapter III requirements, establish a quality management system, and cooperate with authorities.",
        risk_tier="high_risk",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART16_a",
                description="AI system complies with Art. 8-15 requirements",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART16_b",
                description="Contact person designated for authorities",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART16_c",
                description="Quality management system in place (Art. 17)",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART16_f",
                description="Conformity assessment performed (Art. 43)",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART16_j",
                description="Post-market monitoring system established (Art. 72)",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 17",
        title="Quality Management System",
        summary="Providers shall establish a documented quality management system covering development, testing, validation, data management, risk management, and post-market monitoring.",
        risk_tier="high_risk",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART17_1a",
                description="Strategy for regulatory compliance documented",
                check_type="document",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART17_1b",
                description="Design and development procedures",
                check_type="document",
                scanner_fields=["has_development_process_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART17_1c",
                description="Testing and validation procedures",
                check_type="document",
                scanner_fields=["has_test_suite"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART17_1e",
                description="Risk management procedures",
                check_type="document",
                scanner_fields=["has_risk_assessment"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART17_1g",
                description="Incident reporting procedures",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),

    # ===== CHAPTER III, SECTION 4: DEPLOYER OBLIGATIONS =====
    ArticleTaxonomy(
        article="Article 26",
        title="Obligations of Deployers",
        summary="Deployers shall use high-risk AI in accordance with instructions, ensure human oversight, monitor operation, and inform affected persons.",
        risk_tier="high_risk",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART26_1",
                description="Use AI system in accordance with instructions for use",
                check_type="questionnaire",
                scanner_fields=["has_user_instructions"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART26_2",
                description="Assign human oversight to competent persons",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART26_5",
                description="Monitor operation and report malfunctions",
                check_type="questionnaire",
                scanner_fields=["has_logging_config"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART26_7",
                description="Inform affected persons about AI use",
                check_type="questionnaire",
                scanner_fields=["has_ai_disclosure"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART26_9",
                description="Workplace: inform workers' representatives",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 27",
        title="Fundamental Rights Impact Assessment",
        summary="Deployers of high-risk AI (public bodies and private entities in banking, insurance, etc.) shall perform a fundamental rights impact assessment before deployment.",
        risk_tier="high_risk",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART27_1a",
                description="Description of deployer's processes using AI",
                check_type="document",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART27_1b",
                description="Duration and frequency of AI use",
                check_type="document",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART27_1c",
                description="Categories of affected persons",
                check_type="document",
                scanner_fields=["detected_domains"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART27_1d",
                description="Specific risks to identified groups",
                check_type="document",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART27_1f",
                description="Human oversight and complaint mechanisms",
                check_type="document",
                scanner_fields=["has_human_oversight_docs"],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),

    # ===== CHAPTER IV: TRANSPARENCY FOR CERTAIN AI =====
    ArticleTaxonomy(
        article="Article 50",
        title="Transparency Obligations for All AI Systems",
        summary="Providers must ensure persons interacting with AI are informed, AI-generated content is marked, and deep fakes are labeled.",
        risk_tier="all",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART50_1",
                description="AI interaction disclosure",
                check_type="automated",
                scanner_fields=["has_ai_disclosure"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART50_2",
                description="Synthetic content marking (watermarking)",
                check_type="automated",
                scanner_fields=["has_synthetic_content_marking"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART50_4",
                description="Provider identification accessible",
                check_type="automated",
                scanner_fields=["has_provider_identification"],
                covered=True,
            ),
        ],
        enforcement_date="2025-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),

    # ===== CHAPTER V: GENERAL-PURPOSE AI =====
    ArticleTaxonomy(
        article="Article 53",
        title="Obligations for General-Purpose AI Model Providers",
        summary="GPAI model providers must maintain technical documentation, provide information to downstream providers, comply with copyright, and publish a training content summary.",
        risk_tier="general_purpose",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART53_1a",
                description="Technical documentation maintained and updated",
                check_type="document",
                scanner_fields=["has_model_card", "has_architecture_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART53_1b",
                description="Information provided to downstream AI system providers",
                check_type="document",
                scanner_fields=["has_user_instructions"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART53_1c",
                description="Copyright compliance policy",
                check_type="questionnaire",
                scanner_fields=[],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART53_1d",
                description="Detailed summary of training content published",
                check_type="document",
                scanner_fields=["has_data_documentation"],
                covered=True,
            ),
        ],
        enforcement_date="2025-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
    ArticleTaxonomy(
        article="Article 55",
        title="Obligations for Systemic Risk GPAI Models",
        summary="Providers of GPAI models with systemic risk must perform model evaluations, assess and mitigate systemic risks, track and report serious incidents, and ensure cybersecurity.",
        risk_tier="general_purpose",
        severity="critical",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART55_1a",
                description="Model evaluation including adversarial testing",
                check_type="document",
                scanner_fields=["performance_metrics", "has_cybersecurity_docs"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART55_1b",
                description="Systemic risk assessment and mitigation",
                check_type="document",
                scanner_fields=["has_risk_assessment"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART55_1c",
                description="Serious incident tracking and reporting",
                check_type="questionnaire",
                scanner_fields=["has_risk_event_logging"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART55_1d",
                description="Adequate cybersecurity protection",
                check_type="document",
                scanner_fields=["has_cybersecurity_docs"],
                covered=True,
            ),
        ],
        enforcement_date="2025-08-02",
        penalty_reference="Up to 35M EUR or 7% of global annual turnover",
    ),

    # ===== CHAPTER XII: POST-MARKET =====
    ArticleTaxonomy(
        article="Article 72",
        title="Post-Market Monitoring",
        summary="Providers shall establish a post-market monitoring system proportionate to the nature and risks of the AI system.",
        risk_tier="high_risk",
        severity="high",
        check_type="automated",
        coverage="full",
        requirements=[
            ArticleRequirement(
                requirement_id="ART72_1",
                description="Post-market monitoring system established",
                check_type="questionnaire",
                scanner_fields=["has_logging_config", "has_mitigation_plan"],
                covered=True,
            ),
            ArticleRequirement(
                requirement_id="ART72_2",
                description="Monitoring plan documented and updated",
                check_type="document",
                scanner_fields=[],
                covered=True,
            ),
        ],
        enforcement_date="2026-08-02",
        penalty_reference="Up to 15M EUR or 3% of global annual turnover",
    ),
]


def get_taxonomy_summary() -> dict:
    """Return taxonomy summary statistics."""
    total = len(EU_AI_ACT_TAXONOMY)
    automated = sum(1 for a in EU_AI_ACT_TAXONOMY if a.check_type == "automated")
    questionnaire = sum(1 for a in EU_AI_ACT_TAXONOMY if a.check_type == "questionnaire")
    document = sum(1 for a in EU_AI_ACT_TAXONOMY if a.check_type == "document")
    covered_full = sum(1 for a in EU_AI_ACT_TAXONOMY if a.coverage == "full")
    covered_planned = sum(1 for a in EU_AI_ACT_TAXONOMY if a.coverage == "planned")

    total_requirements = sum(len(a.requirements) for a in EU_AI_ACT_TAXONOMY)
    covered_requirements = sum(
        sum(1 for r in a.requirements if r.covered)
        for a in EU_AI_ACT_TAXONOMY
    )

    return {
        "total_articles": total,
        "automated": automated,
        "questionnaire": questionnaire,
        "document": document,
        "coverage": {
            "full": covered_full,
            "planned": covered_planned,
            "requirements_covered": covered_requirements,
            "requirements_total": total_requirements,
            "percentage": round(covered_requirements / total_requirements * 100) if total_requirements else 0,
        },
    }
