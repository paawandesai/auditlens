"""Global AI compliance jurisdiction taxonomy.

Maps all relevant AI compliance laws worldwide with their status,
enforcement dates, requirements overlap with our scanner signals,
and coverage status (supported vs coming soon).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

JurisdictionStatus = Literal["supported", "coming_soon", "research"]
LawStatus = Literal["active", "enacted", "proposed"]


class RequirementOverlap(BaseModel):
    """How a law's requirement maps to our scanner signals."""

    requirement: str
    description: str
    scanner_fields: list[str]
    overlap_strength: Literal["direct", "partial", "none"]


class JurisdictionLaw(BaseModel):
    """A single AI compliance law or regulation."""

    law_id: str
    full_name: str
    short_name: str
    jurisdiction: str
    jurisdiction_type: Literal["supranational", "national", "state", "city", "standard"]
    law_status: LawStatus
    enforcement_date: str | None
    summary: str
    applies_to: list[str]  # e.g., ["employers", "deployers", "developers"]
    sectors: list[str]  # e.g., ["employment", "credit", "education"]
    penalty_summary: str
    requirement_overlaps: list[RequirementOverlap]
    coverage_status: JurisdictionStatus
    scanner_coverage_pct: int  # 0-100, how much our scanner already covers


# ---------------------------------------------------------------------------
# All jurisdictions
# ---------------------------------------------------------------------------

JURISDICTIONS: list[JurisdictionLaw] = [
    # ===== SUPPORTED =====
    JurisdictionLaw(
        law_id="eu_ai_act",
        full_name="Regulation (EU) 2024/1689 — Artificial Intelligence Act",
        short_name="EU AI Act",
        jurisdiction="European Union",
        jurisdiction_type="supranational",
        law_status="enacted",
        enforcement_date="2026-08-02",
        summary="Comprehensive risk-based AI regulation. Prohibits certain AI practices, imposes strict requirements on high-risk AI systems (employment, credit, education, law enforcement), and mandates transparency for all AI.",
        applies_to=["providers", "deployers", "importers", "distributors"],
        sectors=["employment", "credit", "education", "law_enforcement", "critical_infrastructure", "biometrics", "migration", "justice"],
        penalty_summary="Up to 35M EUR or 7% of global annual turnover (prohibited practices); 15M EUR or 3% (other violations)",
        requirement_overlaps=[
            RequirementOverlap(requirement="Risk management system", description="Art. 9: Identify, analyze, and mitigate risks", scanner_fields=["has_risk_assessment", "has_failure_modes_doc", "has_mitigation_plan"], overlap_strength="direct"),
            RequirementOverlap(requirement="Data governance", description="Art. 10: Data quality, provenance, bias examination", scanner_fields=["has_data_documentation", "has_bias_mitigation_docs", "training_data_stats"], overlap_strength="direct"),
            RequirementOverlap(requirement="Technical documentation", description="Art. 11: Model card, architecture, performance", scanner_fields=["has_model_card", "has_architecture_docs", "performance_metrics"], overlap_strength="direct"),
            RequirementOverlap(requirement="Record-keeping", description="Art. 12: Logging, versioning, audit trail", scanner_fields=["has_logging_config", "has_versioning"], overlap_strength="direct"),
            RequirementOverlap(requirement="Transparency", description="Art. 13, 50: Explainability, disclosure, instructions", scanner_fields=["has_explainability", "has_ai_disclosure", "has_user_instructions"], overlap_strength="direct"),
            RequirementOverlap(requirement="Human oversight", description="Art. 14: Override, escalation, stop mechanism", scanner_fields=["has_human_oversight_docs", "has_override_mechanism", "has_stop_mechanism"], overlap_strength="direct"),
            RequirementOverlap(requirement="Accuracy and robustness", description="Art. 15: Testing, adversarial resilience, cybersecurity", scanner_fields=["performance_metrics", "has_cybersecurity_docs", "has_test_suite"], overlap_strength="direct"),
        ],
        coverage_status="supported",
        scanner_coverage_pct=85,
    ),

    # ===== COMING SOON — US STATE/CITY =====
    JurisdictionLaw(
        law_id="colorado_sb24_205",
        full_name="Colorado Senate Bill 24-205 — Concerning Consumer Protections for Artificial Intelligence",
        short_name="Colorado SB24-205",
        jurisdiction="Colorado, USA",
        jurisdiction_type="state",
        law_status="active",
        enforcement_date="2026-02-01",
        summary="Requires developers and deployers of high-risk AI systems to use reasonable care to avoid algorithmic discrimination. Mandates impact assessments, risk management, transparency notices to consumers, and annual reviews.",
        applies_to=["developers", "deployers"],
        sectors=["employment", "credit", "education", "healthcare", "insurance", "housing", "government"],
        penalty_summary="Enforced by Colorado Attorney General; violations treated as deceptive trade practices. No specific fine cap — AG discretion.",
        requirement_overlaps=[
            RequirementOverlap(requirement="Impact assessment", description="Developers must document known risks of algorithmic discrimination", scanner_fields=["has_risk_assessment", "has_bias_mitigation_docs"], overlap_strength="direct"),
            RequirementOverlap(requirement="Risk management policy", description="Deployers must implement risk management policy and procedures", scanner_fields=["has_risk_assessment", "has_mitigation_plan"], overlap_strength="direct"),
            RequirementOverlap(requirement="Transparency notice", description="Consumers must be notified when AI makes consequential decisions", scanner_fields=["has_ai_disclosure", "has_user_instructions"], overlap_strength="direct"),
            RequirementOverlap(requirement="Bias testing", description="Annual review for algorithmic discrimination", scanner_fields=["has_bias_mitigation_docs", "has_data_documentation"], overlap_strength="partial"),
            RequirementOverlap(requirement="Explainability", description="Consumers can request explanation of AI decision", scanner_fields=["has_explainability", "has_feature_importance_docs"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=60,
    ),
    JurisdictionLaw(
        law_id="nyc_ll144",
        full_name="New York City Local Law 144 of 2021 — Automated Employment Decision Tools",
        short_name="NYC Local Law 144",
        jurisdiction="New York City, USA",
        jurisdiction_type="city",
        law_status="active",
        enforcement_date="2023-07-05",
        summary="Requires bias audits of automated employment decision tools (AEDTs) used in hiring and promotion in NYC. Annual independent audits, published results, and candidate notification required.",
        applies_to=["employers", "employment_agencies"],
        sectors=["employment"],
        penalty_summary="$500 per violation (first), $500-$1,500 per subsequent violation per day",
        requirement_overlaps=[
            RequirementOverlap(requirement="Annual bias audit", description="Independent auditor must test for disparate impact by race/ethnicity and sex", scanner_fields=["has_bias_mitigation_docs", "has_data_documentation"], overlap_strength="partial"),
            RequirementOverlap(requirement="Published audit results", description="Summary of bias audit must be publicly available", scanner_fields=["has_model_card"], overlap_strength="partial"),
            RequirementOverlap(requirement="Candidate notification", description="Candidates must be notified of AEDT use at least 10 business days before", scanner_fields=["has_ai_disclosure"], overlap_strength="direct"),
            RequirementOverlap(requirement="Data retention disclosure", description="Must disclose data collected and retention policy", scanner_fields=["has_data_documentation", "has_input_data_recording"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=45,
    ),
    JurisdictionLaw(
        law_id="illinois_aivra",
        full_name="Illinois Artificial Intelligence Video Interview Act (820 ILCS 42)",
        short_name="Illinois AI Video Interview Act",
        jurisdiction="Illinois, USA",
        jurisdiction_type="state",
        law_status="active",
        enforcement_date="2020-01-01",
        summary="Requires employers using AI to analyze video interviews to: notify applicants, explain how AI works, obtain consent, limit sharing, and destroy videos upon request.",
        applies_to=["employers"],
        sectors=["employment"],
        penalty_summary="$1,000 per violation; private right of action",
        requirement_overlaps=[
            RequirementOverlap(requirement="Applicant notification", description="Notify applicant AI will be used to analyze interview", scanner_fields=["has_ai_disclosure"], overlap_strength="direct"),
            RequirementOverlap(requirement="AI explanation", description="Explain how AI works and what characteristics it evaluates", scanner_fields=["has_explainability", "has_user_instructions"], overlap_strength="partial"),
            RequirementOverlap(requirement="Consent required", description="Obtain applicant consent before using AI analysis", scanner_fields=["has_human_oversight_docs"], overlap_strength="partial"),
            RequirementOverlap(requirement="Data destruction", description="Destroy video within 30 days of applicant request", scanner_fields=["has_input_data_recording"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=35,
    ),
    JurisdictionLaw(
        law_id="maryland_hb1202",
        full_name="Maryland House Bill 1202 — Facial Recognition in Hiring",
        short_name="Maryland HB 1202",
        jurisdiction="Maryland, USA",
        jurisdiction_type="state",
        law_status="active",
        enforcement_date="2020-10-01",
        summary="Prohibits employers from using facial recognition technology during job interviews without applicant consent. Applies specifically to facial recognition services.",
        applies_to=["employers"],
        sectors=["employment"],
        penalty_summary="Enforced by MD Commissioner of Labor; civil penalties",
        requirement_overlaps=[
            RequirementOverlap(requirement="Consent for facial recognition", description="Must obtain signed waiver from applicant", scanner_fields=["has_biometric_identification", "has_ai_disclosure"], overlap_strength="direct"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=30,
    ),
    JurisdictionLaw(
        law_id="california_ab2930",
        full_name="California AB 2930 — Automated Decision Tools",
        short_name="California AB 2930",
        jurisdiction="California, USA",
        jurisdiction_type="state",
        law_status="proposed",
        enforcement_date=None,
        summary="Would require deployers of automated decision tools to perform impact assessments, provide notice and opt-out rights, and ensure human review of consequential decisions.",
        applies_to=["deployers"],
        sectors=["employment", "credit", "education", "healthcare", "insurance", "housing"],
        penalty_summary="Proposed: enforced by CA Attorney General",
        requirement_overlaps=[
            RequirementOverlap(requirement="Impact assessment", description="Annual impact assessment for algorithmic discrimination", scanner_fields=["has_risk_assessment", "has_bias_mitigation_docs"], overlap_strength="direct"),
            RequirementOverlap(requirement="Notice and opt-out", description="Consumers informed of AI use with opt-out option", scanner_fields=["has_ai_disclosure", "has_human_oversight_docs"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=40,
    ),

    # ===== COMING SOON — INTERNATIONAL =====
    JurisdictionLaw(
        law_id="canada_aida",
        full_name="Canada Artificial Intelligence and Data Act (Part 3 of Bill C-27)",
        short_name="Canada AIDA",
        jurisdiction="Canada",
        jurisdiction_type="national",
        law_status="proposed",
        enforcement_date=None,
        summary="Would establish requirements for high-impact AI systems: risk assessment, mitigation measures, monitoring, transparency, and record-keeping. Part of the broader Digital Charter Implementation Act.",
        applies_to=["developers", "operators"],
        sectors=["employment", "credit", "healthcare", "law_enforcement", "essential_services"],
        penalty_summary="Proposed: up to 10M CAD or 3% of global revenue (administrative); criminal penalties for reckless AI causing serious harm",
        requirement_overlaps=[
            RequirementOverlap(requirement="Risk assessment", description="Assess and mitigate risks of high-impact systems", scanner_fields=["has_risk_assessment", "has_mitigation_plan"], overlap_strength="direct"),
            RequirementOverlap(requirement="Monitoring", description="Monitor AI systems for compliance and harm", scanner_fields=["has_logging_config", "has_mitigation_plan"], overlap_strength="partial"),
            RequirementOverlap(requirement="Transparency", description="Publish descriptions of high-impact AI systems", scanner_fields=["has_model_card", "has_ai_disclosure"], overlap_strength="direct"),
            RequirementOverlap(requirement="Record-keeping", description="Maintain records of risk assessments and mitigation", scanner_fields=["has_logging_config", "has_risk_assessment"], overlap_strength="direct"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=55,
    ),
    JurisdictionLaw(
        law_id="brazil_ai_act",
        full_name="Brazil AI Regulation Framework (PL 2338/2023)",
        short_name="Brazil AI Act",
        jurisdiction="Brazil",
        jurisdiction_type="national",
        law_status="proposed",
        enforcement_date=None,
        summary="Risk-based framework modeled on EU AI Act. Requires impact assessments for high-risk AI, transparency, human oversight, and algorithmic auditing rights.",
        applies_to=["providers", "deployers"],
        sectors=["employment", "credit", "education", "healthcare", "law_enforcement", "public_services"],
        penalty_summary="Proposed: up to 2% of revenue in Brazil or 50M BRL",
        requirement_overlaps=[
            RequirementOverlap(requirement="Algorithmic impact assessment", description="Mandatory for high-risk systems", scanner_fields=["has_risk_assessment", "has_bias_mitigation_docs"], overlap_strength="direct"),
            RequirementOverlap(requirement="Human oversight", description="Right to human review of automated decisions", scanner_fields=["has_human_oversight_docs", "has_override_mechanism"], overlap_strength="direct"),
            RequirementOverlap(requirement="Transparency", description="Clear information about AI use", scanner_fields=["has_ai_disclosure", "has_explainability"], overlap_strength="direct"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=50,
    ),
    JurisdictionLaw(
        law_id="south_korea_ai_act",
        full_name="South Korea AI Basic Act (Framework Act on AI)",
        short_name="South Korea AI Act",
        jurisdiction="South Korea",
        jurisdiction_type="national",
        law_status="enacted",
        enforcement_date="2026-01-22",
        summary="Establishes principles for trustworthy AI: risk classification, impact assessments for high-risk AI, transparency, and an AI Committee for governance.",
        applies_to=["developers", "deployers", "operators"],
        sectors=["employment", "credit", "healthcare", "education", "public_safety"],
        penalty_summary="Administrative fines; specific amounts TBD by presidential decree",
        requirement_overlaps=[
            RequirementOverlap(requirement="Risk classification", description="Classify AI systems by risk level", scanner_fields=["risk_classification", "detected_domains"], overlap_strength="direct"),
            RequirementOverlap(requirement="Impact assessment", description="High-impact AI requires impact assessment", scanner_fields=["has_risk_assessment"], overlap_strength="direct"),
            RequirementOverlap(requirement="Transparency", description="Users informed of AI interaction", scanner_fields=["has_ai_disclosure"], overlap_strength="direct"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=40,
    ),
    JurisdictionLaw(
        law_id="china_algo_recommendation",
        full_name="China Provisions on the Management of Algorithmic Recommendations",
        short_name="China Algorithm Regulation",
        jurisdiction="China",
        jurisdiction_type="national",
        law_status="active",
        enforcement_date="2022-03-01",
        summary="Regulates algorithmic recommendation services. Requires algorithm transparency, user opt-out rights, protection of minors, and filing with authorities. Supplemented by deep synthesis and generative AI rules.",
        applies_to=["algorithm_recommendation_service_providers"],
        sectors=["media", "ecommerce", "social_media", "content_platforms"],
        penalty_summary="Warnings, fines up to 100K RMB, service suspension",
        requirement_overlaps=[
            RequirementOverlap(requirement="Algorithm transparency", description="Explain basic principles of algorithm", scanner_fields=["has_explainability", "has_model_card"], overlap_strength="partial"),
            RequirementOverlap(requirement="User controls", description="Allow users to opt out of algorithmic recommendations", scanner_fields=["has_human_oversight_docs", "has_override_mechanism"], overlap_strength="partial"),
            RequirementOverlap(requirement="Algorithm filing", description="Register algorithm with authorities", scanner_fields=[], overlap_strength="none"),
        ],
        coverage_status="research",
        scanner_coverage_pct=20,
    ),

    JurisdictionLaw(
        law_id="illinois_bipa",
        full_name="Illinois Biometric Information Privacy Act (740 ILCS 14)",
        short_name="Illinois BIPA",
        jurisdiction="Illinois, USA",
        jurisdiction_type="state",
        law_status="active",
        enforcement_date="2008-10-03",
        summary="Requires written informed consent before collecting biometric data (face, voice, fingerprint). Written retention/destruction policy required. No sale of biometric data. Applies when AI uses facial/voice recognition.",
        applies_to=["employers", "private_entities"],
        sectors=["employment", "biometrics", "access_control"],
        penalty_summary="$1,000 per negligent violation; $5,000 per intentional violation. Private right of action.",
        requirement_overlaps=[
            RequirementOverlap(requirement="Informed consent", description="Written consent before biometric collection", scanner_fields=["has_ai_disclosure", "has_biometric_identification"], overlap_strength="direct"),
            RequirementOverlap(requirement="Retention policy", description="Written policy on retention and destruction", scanner_fields=["has_input_data_recording", "has_data_documentation"], overlap_strength="partial"),
            RequirementOverlap(requirement="Data security", description="Reasonable security for biometric data", scanner_fields=["has_cybersecurity_docs"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=35,
    ),
    JurisdictionLaw(
        law_id="california_ab2013",
        full_name="California Assembly Bill 2013 — AI Training Data Transparency",
        short_name="California AB 2013",
        jurisdiction="California, USA",
        jurisdiction_type="state",
        law_status="enacted",
        enforcement_date="2026-01-01",
        summary="Developers of generative AI must publish documentation about training data: high-level summary of datasets, whether personal data was included, and whether data was purchased or scraped.",
        applies_to=["developers"],
        sectors=["generative_ai"],
        penalty_summary="Enforced under existing consumer protection law by AG.",
        requirement_overlaps=[
            RequirementOverlap(requirement="Training data documentation", description="Publish summary of training datasets", scanner_fields=["has_data_documentation", "training_data_stats"], overlap_strength="direct"),
            RequirementOverlap(requirement="Data provenance", description="Disclose data sources and collection methods", scanner_fields=["has_data_documentation"], overlap_strength="direct"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=50,
    ),
    JurisdictionLaw(
        law_id="california_sb942",
        full_name="California Senate Bill 942 — California AI Transparency Act",
        short_name="California SB 942",
        jurisdiction="California, USA",
        jurisdiction_type="state",
        law_status="enacted",
        enforcement_date="2026-01-01",
        summary="GenAI providers must offer AI detection tools, include provenance data in AI-generated content (watermark/metadata), and enable system-level provenance tracking.",
        applies_to=["providers"],
        sectors=["generative_ai"],
        penalty_summary="Enforceable by AG, city attorneys, county counsel.",
        requirement_overlaps=[
            RequirementOverlap(requirement="Content provenance", description="Watermark or metadata in AI-generated content", scanner_fields=["has_synthetic_content_marking", "has_ai_disclosure"], overlap_strength="direct"),
            RequirementOverlap(requirement="Detection tools", description="Provide free AI content detection", scanner_fields=["has_test_suite"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=40,
    ),
    JurisdictionLaw(
        law_id="connecticut_sb2",
        full_name="Connecticut Senate Bill 2 — An Act Concerning Artificial Intelligence",
        short_name="Connecticut SB 2",
        jurisdiction="Connecticut, USA",
        jurisdiction_type="state",
        law_status="enacted",
        enforcement_date="2026-01-01",
        summary="Impact assessments for high-risk AI systems. Consumer notification, right to explanation, opt-out mechanisms. Developer disclosure requirements. Modeled after Colorado SB24-205.",
        applies_to=["developers", "deployers"],
        sectors=["employment", "credit", "education", "healthcare", "housing", "insurance"],
        penalty_summary="AG enforcement; civil penalties.",
        requirement_overlaps=[
            RequirementOverlap(requirement="Impact assessment", description="Assess risks of algorithmic discrimination", scanner_fields=["has_risk_assessment", "has_bias_mitigation_docs"], overlap_strength="direct"),
            RequirementOverlap(requirement="Consumer notification", description="Inform consumers of AI use in consequential decisions", scanner_fields=["has_ai_disclosure", "has_user_instructions"], overlap_strength="direct"),
            RequirementOverlap(requirement="Right to explanation", description="Consumers can request explanation of AI decision", scanner_fields=["has_explainability", "has_feature_importance_docs"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=55,
    ),
    JurisdictionLaw(
        law_id="eu_gdpr_art22",
        full_name="EU General Data Protection Regulation — Article 22 (Automated Decision-Making)",
        short_name="EU GDPR Art. 22",
        jurisdiction="European Union",
        jurisdiction_type="supranational",
        law_status="active",
        enforcement_date="2018-05-25",
        summary="Right not to be subject to solely automated decision-making with legal/significant effects. Right to explanation. Data protection impact assessments for high-risk AI processing. Applies to any AI using personal data of EU residents.",
        applies_to=["data_controllers", "data_processors"],
        sectors=["all"],
        penalty_summary="Up to 20M EUR or 4% of global annual turnover.",
        requirement_overlaps=[
            RequirementOverlap(requirement="Right to explanation", description="Art. 22: Explain automated decisions", scanner_fields=["has_explainability", "has_feature_importance_docs"], overlap_strength="direct"),
            RequirementOverlap(requirement="Human review", description="Art. 22: Right to human intervention", scanner_fields=["has_human_oversight_docs", "has_override_mechanism"], overlap_strength="direct"),
            RequirementOverlap(requirement="DPIA", description="Data protection impact assessment for high-risk processing", scanner_fields=["has_risk_assessment"], overlap_strength="direct"),
            RequirementOverlap(requirement="Data governance", description="Lawful basis, data minimization, purpose limitation", scanner_fields=["has_data_documentation"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=50,
    ),

    # ===== COMING SOON — STANDARDS / FRAMEWORKS =====
    JurisdictionLaw(
        law_id="iso_42001",
        full_name="ISO/IEC 42001:2023 — AI Management System",
        short_name="ISO 42001",
        jurisdiction="International",
        jurisdiction_type="standard",
        law_status="active",
        enforcement_date="2023-12-18",
        summary="International standard for establishing, implementing, and maintaining an AI management system (AIMS). Covers risk management, data governance, documentation, and continuous improvement.",
        applies_to=["providers", "deployers", "any_organization"],
        sectors=["all"],
        penalty_summary="No direct penalties — voluntary certification. Required by some procurement and regulatory frameworks.",
        requirement_overlaps=[
            RequirementOverlap(requirement="AI risk management", description="Clause 6.1: Risk assessment and treatment", scanner_fields=["has_risk_assessment", "has_mitigation_plan"], overlap_strength="direct"),
            RequirementOverlap(requirement="Data management", description="Annex B: Data quality, provenance, governance", scanner_fields=["has_data_documentation", "training_data_stats"], overlap_strength="direct"),
            RequirementOverlap(requirement="Documentation", description="Clause 7.5: Documented information", scanner_fields=["has_model_card", "has_architecture_docs"], overlap_strength="direct"),
            RequirementOverlap(requirement="Performance evaluation", description="Clause 9: Monitoring, measurement, analysis", scanner_fields=["performance_metrics", "has_logging_config"], overlap_strength="direct"),
            RequirementOverlap(requirement="Continuous improvement", description="Clause 10: Corrective action and improvement", scanner_fields=["has_versioning", "has_test_suite"], overlap_strength="partial"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=50,
    ),
    JurisdictionLaw(
        law_id="nist_ai_rmf",
        full_name="NIST AI Risk Management Framework (AI RMF 1.0)",
        short_name="NIST AI RMF",
        jurisdiction="United States",
        jurisdiction_type="national",
        law_status="active",
        enforcement_date="2023-01-26",
        summary="Voluntary framework for managing AI risks. Four core functions: Govern, Map, Measure, Manage. Referenced by US Executive Order 14110 and increasingly adopted as compliance benchmark.",
        applies_to=["developers", "deployers", "any_organization"],
        sectors=["all"],
        penalty_summary="Voluntary — no direct penalties. Increasingly referenced in federal procurement and regulation.",
        requirement_overlaps=[
            RequirementOverlap(requirement="GOVERN: Policies and processes", description="Establish AI governance structure", scanner_fields=["has_risk_assessment"], overlap_strength="partial"),
            RequirementOverlap(requirement="MAP: Context and risk framing", description="Identify AI system context and potential impacts", scanner_fields=["detected_domains", "risk_classification"], overlap_strength="direct"),
            RequirementOverlap(requirement="MEASURE: Assessment", description="Analyze and track AI risks and impacts", scanner_fields=["performance_metrics", "has_bias_mitigation_docs", "has_test_suite"], overlap_strength="direct"),
            RequirementOverlap(requirement="MANAGE: Mitigate and monitor", description="Prioritize and act on AI risks", scanner_fields=["has_mitigation_plan", "has_logging_config", "has_human_oversight_docs"], overlap_strength="direct"),
        ],
        coverage_status="coming_soon",
        scanner_coverage_pct=45,
    ),
]


def get_jurisdictions_summary() -> dict:
    """Return jurisdiction summary statistics."""
    supported = [j for j in JURISDICTIONS if j.coverage_status == "supported"]
    coming_soon = [j for j in JURISDICTIONS if j.coverage_status == "coming_soon"]
    research = [j for j in JURISDICTIONS if j.coverage_status == "research"]

    return {
        "total_jurisdictions": len(JURISDICTIONS),
        "supported": len(supported),
        "coming_soon": len(coming_soon),
        "research": len(research),
        "active_laws": sum(1 for j in JURISDICTIONS if j.law_status == "active"),
        "enacted_laws": sum(1 for j in JURISDICTIONS if j.law_status == "enacted"),
        "proposed_laws": sum(1 for j in JURISDICTIONS if j.law_status == "proposed"),
    }
