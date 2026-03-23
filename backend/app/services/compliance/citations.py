"""EU AI Act regulatory citations for evidence descriptions.

Each constant maps sub-check names to specific article/paragraph references
from Regulation (EU) 2024/1689. Used by article checks to ground evidence
text in the actual regulatory text.
"""

ART_9: dict[str, str] = {
    "risk_assessment": "[Art. 9(2)(a)] Identification and analysis of known and foreseeable risks",
    "failure_modes": "[Art. 9(2)(b)] Risk estimation under conditions of foreseeable misuse",
    "mitigation": "[Art. 9(2)(d)] Targeted risk management measures adopted",
    "residual_risk": "[Art. 9(5)] Residual risk judged acceptable after mitigation",
    "testing_metrics": "[Art. 9(6)] Testing against prior-defined metrics before placing on market",
}

ART_10: dict[str, str] = {
    "provenance": "[Art. 10(2)(b)] Training data provenance and collection methodology",
    "bias": "[Art. 10(2)(f-g)] Examination for possible biases relevant to health/safety/rights",
    "quality": "[Art. 10(3)] Data quality criteria: relevance, representativeness, completeness",
    "preprocessing": "[Art. 10(2)(e)] Data preparation and preprocessing operations",
    "bias_mitigation": "[Art. 10(2)(g)] Measures to detect, prevent, and mitigate biases",
    "data_gaps": "[Art. 10(2)(h)] Identification of relevant data gaps or shortcomings",
}

ART_11: dict[str, str] = {
    "model_card": "[Art. 11(1), Annex IV] Technical documentation drawn up before placing on market",
    "architecture": "[Annex IV §2(b)] System architecture and design specifications",
    "performance": "[Annex IV §3] Performance metrics on validation and testing data",
    "dev_process": "[Annex IV §2(a-c)] Development methods, design specs, and training methodology",
    "standards": "[Annex IV §8] List of harmonised standards or common specifications applied",
}

ART_12: dict[str, str] = {
    "logging": "[Art. 12(1)] Automatic recording of events (logs) during operation",
    "versioning": "[Art. 12(2)] Traceability of AI system functioning throughout lifecycle",
    "audit_trail": "[Art. 12(1)] Logs enabling monitoring of operation and post-market surveillance",
    "risk_events": "[Art. 12(2)(a)] Logging of events identifying risk situations",
    "input_recording": "[Art. 12(3)(c)] Recording of input data for which the system was used",
}

ART_13: dict[str, str] = {
    "explainability": "[Art. 13(3)(d)] Level of accuracy and robustness transparency",
    "feature_importance": "[Art. 13(3)(b)(iv)] Relevant information about training data",
    "user_instructions": "[Art. 13(3)] Instructions for use for deployers",
    "capabilities": "[Art. 13(3)(b)] Description of capabilities and limitations",
    "group_performance": "[Art. 13(3)(b)(v)] Performance for specific groups of persons",
}

ART_14: dict[str, str] = {
    "human_in_loop": "[Art. 14(1)] Human oversight measures built into or identified by provider",
    "override": "[Art. 14(4)(d)] Ability to override or reverse AI system output",
    "escalation": "[Art. 14(4)(c)] Correctly interpret high-risk AI system's output",
    "automation_bias": "[Art. 14(4)(b)] Awareness of possible automation bias tendency",
    "stop_mechanism": "[Art. 14(4)(e)] Stop button or similar procedure for safe halt",
}

ART_15: dict[str, str] = {
    "test_metrics": "[Art. 15(2)] Appropriate level of accuracy for intended purpose",
    "adversarial": "[Art. 15(5)] Resilience against adversarial examples and model evasion",
    "versioning": "[Art. 15(4)] Technical redundancy including backup/fail-safe plans",
    "cybersecurity": "[Art. 15(5)] Resilience against data poisoning, model poisoning, confidentiality attacks",
    "feedback_loop": "[Art. 15(4)] Measures to eliminate/reduce biased output feedback loops",
    "error_resilience": "[Art. 15(4)] Resilient to errors, faults, and inconsistencies",
}

ART_5: dict[str, str] = {
    "social_scoring": "[Art. 5(1)(c)] Social scoring by public authorities or on their behalf",
    "biometric_identification": (
        "[Art. 5(1)(g)] Real-time remote biometric identification"
        " in publicly accessible spaces for law enforcement"
    ),
    "emotion_inference": (
        "[Art. 5(1)(f)] Emotion recognition in workplace or"
        " educational institutions"
    ),
}

ART_50: dict[str, str] = {
    "ai_interaction_disclosed": (
        "[Art. 50(1)] Persons interacting with an AI system shall"
        " be informed they are interacting with an AI system"
    ),
    "synthetic_content_marked": (
        "[Art. 50(2)] AI-generated or manipulated content shall"
        " be marked in a machine-readable format"
    ),
    "provider_identified": (
        "[Art. 50(4)] Provider name and contact information"
        " shall be accessible to deployers and users"
    ),
}
