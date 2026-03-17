"""Pure-logic content analysis for compliance signal detection.

Two stateless functions that map repository file trees and file contents
onto ScannerOutput boolean fields. No I/O — receives pre-fetched data.
"""

from __future__ import annotations

from fnmatch import fnmatch

# ---------------------------------------------------------------------------
# File-tree patterns → ScannerOutput field mapping
# ---------------------------------------------------------------------------
# Each entry: (ScannerOutput field, list of glob patterns to match against)
# Patterns are matched case-insensitively against the full file path.

FILE_TREE_RULES: list[tuple[str, list[str]]] = [
    ("has_risk_assessment", [
        "*risk_assessment*", "*risk-assessment*", "*risk_management*", "*risk-management*",
        "*RISK_ASSESSMENT*",
    ]),
    ("has_model_card", [
        "*model_card*", "*model-card*", "*MODEL_CARD*",
    ]),
    ("has_architecture_docs", [
        "*ARCHITECTURE*", "docs/design*", "docs/architecture*",
    ]),
    ("has_test_suite", [
        "tests/*", "test/*",
    ]),
    ("has_versioning", [
        ".github/workflows/*", ".dvc/*",
    ]),
    ("has_data_documentation", [
        "*data_card*", "*data-card*", "*dataset_card*", "*dataset-card*", "*datasheet*",
    ]),
    ("has_failure_modes_doc", [
        "tests/risk*", "tests/safety*", "test/risk*", "test/safety*",
    ]),
    ("has_logging_config", [
        "*RETENTION*", "*data_retention*", "*data-retention*",
    ]),
    ("has_model_card_user_instructions", [
        "*USAGE*", "*user_guide*", "*user-guide*", "*deployer_guide*", "*deployer-guide*",
    ]),
]

# Metrics-related file patterns (sets performance_metrics_present flag)
METRICS_FILE_PATTERNS: list[str] = [
    "*eval_results*", "*eval-results*", "*metrics*", "*benchmark*",
]

# Bias-related file patterns (sets bias_analysis_found flag)
BIAS_FILE_PATTERNS: list[str] = [
    "*bias_report*", "*bias-report*", "*fairness_report*", "*fairness-report*",
]

# ---------------------------------------------------------------------------
# Content keyword patterns → ScannerOutput field mapping
# ---------------------------------------------------------------------------
# Each entry: (ScannerOutput field, list of substring/regex patterns)
# Matching is case-insensitive on the combined content string.

CONTENT_RULES: list[tuple[str, list[str]]] = [
    ("has_human_oversight_docs", [
        "human review", "manual review", "human-in-the-loop", "human in the loop",
    ]),
    ("has_override_mechanism", [
        "override", "kill_switch", "kill switch",
    ]),
    ("has_feature_importance_docs", [
        "feature importance",
    ]),
    ("has_explainability", [
        "shap", "lime", "explainab",
    ]),
    ("has_logging_config", [
        "audit log", "logging", "telemetry", "event record",
    ]),
    ("has_mitigation_plan", [
        "monitoring", "drift",
    ]),
]

# Content patterns for TrainingDataStats sub-fields
TRAINING_DATA_CONTENT_RULES: list[tuple[str, list[str]]] = [
    ("provenance_documented", ["data source", "provenance"]),
    ("preprocessing_documented", ["preprocessing", "feature engineer"]),
]

# AI API key variable names — presence in .env.example signals AI usage
ENV_AI_KEY_PATTERNS: list[str] = [
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "COHERE_API_KEY",
    "GOOGLE_AI_KEY", "HUGGINGFACE_TOKEN", "REPLICATE_API_TOKEN",
    "TOGETHER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
]


def check_file_tree_flags(file_paths: list[str]) -> dict[str, bool]:
    """Match file paths against compliance patterns.

    Args:
        file_paths: list of repo-relative paths (e.g. "tests/test_model.py")

    Returns:
        dict with ScannerOutput field names as keys, bool as values.
        Also includes internal flags: ``performance_metrics_present``,
        ``bias_analysis_found``, ``user_instructions_found``.
    """
    lowered = [p.lower() for p in file_paths]

    flags: dict[str, bool] = {}

    for field, patterns in FILE_TREE_RULES:
        matched = any(
            fnmatch(fp, pat.lower())
            for fp in lowered
            for pat in patterns
        )
        # Some fields (e.g. has_logging_config) appear in both file-tree and content
        # rules — use OR so either detection method can flip the flag.
        flags[field] = flags.get(field, False) or matched

    # Internal flags consumed by the scanner to build typed models
    flags["performance_metrics_present"] = any(
        fnmatch(fp, pat.lower()) for fp in lowered for pat in METRICS_FILE_PATTERNS
    )
    flags["bias_analysis_found"] = any(
        fnmatch(fp, pat.lower()) for fp in lowered for pat in BIAS_FILE_PATTERNS
    )
    flags["user_instructions_found"] = any(
        fnmatch(fp, pat.lower())
        for fp in lowered
        for pat in [
            "*usage*", "*user_guide*", "*user-guide*",
            "*deployer_guide*", "*deployer-guide*",
        ]
    )

    return flags


def extract_content_flags(contents: dict[str, str]) -> dict[str, bool | dict[str, bool]]:
    """Keyword-match file contents for compliance signals.

    Args:
        contents: dict mapping filename → file content text.

    Returns:
        dict with ScannerOutput field names as keys.
        Also includes ``training_data_sub`` dict with sub-field bools.
    """
    combined = "\n".join(contents.values()).lower()

    flags: dict[str, bool | dict[str, bool]] = {}

    for field, keywords in CONTENT_RULES:
        matched = any(kw in combined for kw in keywords)
        flags[field] = bool(flags.get(field, False)) or matched

    # Training data sub-field signals
    training_sub: dict[str, bool] = {}
    for sub_field, keywords in TRAINING_DATA_CONTENT_RULES:
        training_sub[sub_field] = any(kw in combined for kw in keywords)
    flags["training_data_sub"] = training_sub

    # Adversarial testing signal
    flags["adversarial_tested"] = any(
        kw in combined for kw in ["adversarial", "robustness test"]
    )

    # AI API key detection (from .env.example or docker-compose.yml)
    upper_combined = "\n".join(contents.values())
    flags["ai_api_keys_found"] = any(
        key in upper_combined for key in ENV_AI_KEY_PATTERNS
    )

    return flags
