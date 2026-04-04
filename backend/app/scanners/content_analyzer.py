"""Pure-logic content analysis for compliance signal detection.

Stateless functions that map repository file trees and file contents
onto ScannerOutput boolean fields. No I/O — receives pre-fetched data.

Includes section-based document validation (ported from Systima Comply,
Apache 2.0) to check whether compliance docs contain required sections.

Phase 2 overhaul: KeywordRule with word boundaries and negative patterns
to reduce false positives from generic keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch

from app.schemas.scanner import DocValidation

# ---------------------------------------------------------------------------
# File-tree patterns → ScannerOutput field mapping
# ---------------------------------------------------------------------------
# Each entry: (ScannerOutput field, list of glob patterns to match against)
# Patterns are matched case-insensitively against the full file path.

FILE_TREE_RULES: list[tuple[str, list[str]]] = [
    ("has_risk_assessment", [
        "*risk_assessment*", "*risk-assessment*", "*risk_management*", "*risk-management*",
        "*RISK_ASSESSMENT*", "*risk_analysis*", "*risk_register*", "compliance/*risk*",
        "*RISK.md",
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
        "*data_provenance*", "*data_lineage*", "*data_manifest*",
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
    # Articles 16, 17, 26, 27, 53, 55, 72 — organizational/GPAI signals
    ("has_contact_info", [
        "SECURITY.md", "SECURITY.rst", "CONTRIBUTING.md", "CONTRIBUTING.rst",
        "MAINTAINERS", "MAINTAINERS.md", "CODEOWNERS", ".github/CODEOWNERS",
        "SUPPORT.md",
    ]),
    ("has_impact_assessment", [
        "*impact_assessment*", "*impact-assessment*", "*FRIA*",
        "*fundamental_rights*", "*fundamental-rights*",
        "*rights_assessment*", "*rights-assessment*",
    ]),
    ("has_monitoring_config", [
        "*alerting*", "*monitoring*", "*grafana*", "*prometheus*",
        "*datadog*", "*sentry*", "monitoring/*", "observability/*",
    ]),
    ("has_qms_docs", [
        "*quality_management*", "*quality-management*", "*QMS*",
        "*quality_policy*", "*quality-policy*",
    ]),
    ("has_conformity_assessment", [
        "*conformity*", "*conformity_assessment*", "*conformity-assessment*",
        "*ce_marking*", "*ce-marking*",
    ]),
    ("has_explainability", [
        "*explainability*", "*interpretability*",
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
# KeywordRule — Phase 2 smart matching infrastructure
# ---------------------------------------------------------------------------

# High-trust file patterns (docs, model cards, risk assessments)
_HIGH_TRUST_PATTERNS = (
    "readme", "model_card", "model-card", "risk_assessment", "risk-assessment",
    "data_card", "data-card", "dataset_card", "datasheet", "docs/",
    "doc/", "guide", "transparency", "human_oversight",
)

# Source code file extensions
_SOURCE_CODE_EXTENSIONS = (
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb",
    ".c", ".cpp", ".h", ".cs", ".swift", ".kt",
)


def _is_high_trust_file(filename: str) -> bool:
    """Check if a filename is a high-trust documentation file."""
    lower = filename.lower()
    return any(pat in lower for pat in _HIGH_TRUST_PATTERNS)


def _is_source_code_file(filename: str) -> bool:
    """Check if a filename is a source code file."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in _SOURCE_CODE_EXTENSIONS)


@dataclass(frozen=True)
class KeywordRule:
    """A keyword matching rule with optional precision controls.

    Attributes:
        keyword: The search term (case-insensitive).
        word_boundary: If True, use \\b regex for exact word matching.
        negative_patterns: Skip match if any of these found nearby.
        require_doc_context: Only match in docs/README, not source code.
        min_source_occurrences: Minimum occurrences needed in source code files.
    """

    keyword: str
    word_boundary: bool = False
    negative_patterns: tuple[str, ...] = ()
    require_doc_context: bool = False
    min_source_occurrences: int = 1


def _matches_keyword_in_text(rule: KeywordRule, text: str) -> bool:
    """Check if a keyword rule matches within a text string (already lowered)."""
    if rule.word_boundary:
        pattern = r"\b" + re.escape(rule.keyword) + r"\b"
        if not re.search(pattern, text, re.IGNORECASE):
            return False
    else:
        if rule.keyword not in text:
            return False

    if rule.negative_patterns:
        for neg in rule.negative_patterns:
            if neg in text:
                return False

    return True


def _matches_keyword_per_file(
    rule: KeywordRule, contents: dict[str, str],
) -> bool:
    """Check if a keyword rule matches across files with context awareness."""
    for filename, content in contents.items():
        lower_content = content.lower()

        if rule.require_doc_context and _is_source_code_file(filename):
            continue

        if _is_source_code_file(filename) and rule.min_source_occurrences > 1:
            if rule.word_boundary:
                pattern = r"\b" + re.escape(rule.keyword) + r"\b"
                count = len(re.findall(pattern, lower_content, re.IGNORECASE))
            else:
                count = lower_content.count(rule.keyword)
            if count >= rule.min_source_occurrences:
                if not rule.negative_patterns or not any(
                    neg in lower_content for neg in rule.negative_patterns
                ):
                    return True
            continue

        if _matches_keyword_in_text(rule, lower_content):
            return True

    return False


# ---------------------------------------------------------------------------
# Content keyword rules → ScannerOutput field mapping (Phase 2 overhaul)
# ---------------------------------------------------------------------------

CONTENT_RULES: list[tuple[str, list[KeywordRule]]] = [
    ("has_human_oversight_docs", [
        KeywordRule("human review"),
        KeywordRule("manual review"),
        KeywordRule("human-in-the-loop"),
        KeywordRule("human in the loop"),
    ]),
    # Phase 2B: "override" → compound phrases only to avoid method/CSS overrides
    ("has_override_mechanism", [
        KeywordRule("override decision"),
        KeywordRule("override output"),
        KeywordRule("override mechanism"),
        KeywordRule("override model"),
        KeywordRule("override ai"),
        KeywordRule("override prediction"),
        KeywordRule("kill_switch"),
        KeywordRule("kill switch"),
    ]),
    ("has_escalation_docs", [
        # Phase 2B: compound only — bare "escalat" hits "escalate privileges"
        KeywordRule("escalation procedure"),
        KeywordRule("escalation path"),
        KeywordRule("escalate to human"),
        KeywordRule("escalation process"),
        KeywordRule("stop button"),
        KeywordRule("halt the system"),
        KeywordRule("interrupt the system"),
        KeywordRule("emergency stop"),
        KeywordRule("safe state"),
    ]),
    ("has_feature_importance_docs", [
        KeywordRule("feature importance"),
        KeywordRule("permutation importance"),
        KeywordRule("shapley value"),
    ]),
    # Phase 2B: word-boundary for shap/lime, keep explainab as substring
    ("has_explainability", [
        KeywordRule("shap", word_boundary=True),
        KeywordRule("lime", word_boundary=True),
        KeywordRule("explainab"),
        KeywordRule("captum"),
        KeywordRule("eli5", word_boundary=True),
        KeywordRule("alibi explain"),
        KeywordRule("interpretml"),
        KeywordRule("counterfactual explanation"),
    ]),
    # Phase 2B: compound phrases only — bare "logging" matches import logging
    ("has_logging_config", [
        KeywordRule("audit log"),
        KeywordRule("audit logging"),
        KeywordRule("event logging"),
        KeywordRule("event record"),
        KeywordRule("decision log"),
        KeywordRule("observability", require_doc_context=True),
        KeywordRule("activity log"),
    ]),
    # Phase 2B: compound phrases only — bare "monitoring"/"drift" are too generic
    ("has_mitigation_plan", [
        KeywordRule("model monitoring"),
        KeywordRule("drift monitoring"),
        KeywordRule("risk monitoring"),
        KeywordRule("ai monitoring"),
        KeywordRule("drift detection"),
        KeywordRule("model drift"),
    ]),
    # --- Phase 3 new fields ---
    # Article 9
    ("has_residual_risk_evaluation", [
        KeywordRule("residual risk"),
        KeywordRule("remaining risk"),
        KeywordRule("accepted risk"),
    ]),
    ("has_testing_metrics_defined", [
        KeywordRule("acceptance criteria"),
        KeywordRule("metric threshold"),
        KeywordRule("test against"),
        KeywordRule("performance threshold"),
    ]),
    # Article 10
    ("has_bias_mitigation_docs", [
        KeywordRule("bias mitigation"),
        KeywordRule("debiasing"),
        KeywordRule("fairness constraint"),
        KeywordRule("rebalancing"),
        KeywordRule("adversarial debiasing"),
        KeywordRule("equalized odds"),
        KeywordRule("demographic parity"),
        KeywordRule("disparity reduction"),
    ]),
    ("has_data_gaps_identified", [
        KeywordRule("data gap"),
        KeywordRule("underrepresented"),
        KeywordRule("missing data"),
        KeywordRule("data limitation"),
        KeywordRule("class imbalance"),
        KeywordRule("sampling bias"),
        KeywordRule("representation gap"),
    ]),
    # Article 11
    ("has_development_process_docs", [
        KeywordRule("design specification"),
        KeywordRule("training methodology"),
        KeywordRule("development process"),
    ]),
    ("has_standards_applied", [
        KeywordRule("harmonised standard"),
        KeywordRule("iso 42001"),
        KeywordRule("iso/iec"),
        KeywordRule("en standard"),
    ]),
    # Article 12
    ("has_risk_event_logging", [
        KeywordRule("risk event"),
        KeywordRule("safety event"),
        KeywordRule("incident log"),
        KeywordRule("anomaly detection"),
    ]),
    ("has_input_data_recording", [
        KeywordRule("input logging"),
        KeywordRule("request logging"),
        KeywordRule("input recording"),
        KeywordRule("data retention"),
    ]),
    # Article 13
    ("has_capabilities_limitations", [
        KeywordRule("known limitation"),
        KeywordRule("intended use"),
        KeywordRule("capabilities and limitation"),
    ]),
    ("has_group_performance_docs", [
        KeywordRule("disaggregated"),
        KeywordRule("group performance"),
        KeywordRule("subgroup analysis"),
        KeywordRule("demographic"),
    ]),
    # Article 14
    ("has_automation_bias_docs", [
        KeywordRule("automation bias"),
        KeywordRule("over-reliance"),
        KeywordRule("human judgment"),
    ]),
    ("has_stop_mechanism", [
        KeywordRule("stop button"),
        KeywordRule("emergency stop"),
        KeywordRule("safe halt"),
        KeywordRule("kill switch"),
        KeywordRule("kill_switch"),
        KeywordRule("circuit breaker"),
        KeywordRule("failsafe"),
    ]),
    # Article 15
    ("has_cybersecurity_docs", [
        KeywordRule("data poisoning"),
        KeywordRule("model poisoning"),
        KeywordRule("adversarial defense"),
        KeywordRule("model evasion"),
        KeywordRule("cybersecurity"),
        KeywordRule("security measure"),
    ]),
    ("has_feedback_loop_prevention", [
        KeywordRule("feedback loop"),
        KeywordRule("recursive bias"),
        KeywordRule("self-reinforcing"),
    ]),
    ("has_error_resilience_docs", [
        KeywordRule("error resilience"),
        KeywordRule("fault tolerance"),
        KeywordRule("graceful degradation"),
        KeywordRule("fail-safe"),
    ]),
    # --- Articles 16, 17, 26, 27, 53, 55, 72 organizational/GPAI signals ---
    ("has_incident_reporting", [
        KeywordRule("incident report"),
        KeywordRule("incident response"),
        KeywordRule("incident management"),
        KeywordRule("post-market surveillance"),
        KeywordRule("serious incident"),
    ]),
    ("has_monitoring_config", [
        KeywordRule("model monitoring"),
        KeywordRule("production monitoring"),
        KeywordRule("performance monitoring", require_doc_context=True),
        KeywordRule("alerting"),
        KeywordRule("drift monitoring"),
    ]),
    ("has_copyright_policy", [
        KeywordRule("copyright policy"),
        KeywordRule("data licensing"),
        KeywordRule("intellectual property"),
        KeywordRule("training data license"),
        KeywordRule("content licensing"),
    ]),
    ("has_impact_assessment", [
        KeywordRule("impact assessment"),
        KeywordRule("fundamental rights"),
        KeywordRule("rights impact"),
        KeywordRule("algorithmic impact"),
    ]),
    ("has_qms_docs", [
        KeywordRule("quality management"),
        KeywordRule("quality assurance"),
        KeywordRule("quality system"),
    ]),
    ("has_conformity_assessment", [
        KeywordRule("conformity assessment"),
        KeywordRule("ce marking"),
        KeywordRule("self-assessment"),
        KeywordRule("third-party audit"),
    ]),
    # --- Article 5 prohibited practice indicators ---
    ("has_social_scoring_indicators", [
        KeywordRule("social score"),
        KeywordRule("citizen score"),
        KeywordRule("social credit"),
        KeywordRule("social scoring"),
    ]),
    ("has_biometric_identification", [
        KeywordRule("real-time biometric"),
        KeywordRule("facial recognition"),
        KeywordRule("face_recognition"),
        KeywordRule("deepface"),
        KeywordRule("insightface"),
        KeywordRule("biometric identification"),
    ]),
    ("has_emotion_inference", [
        KeywordRule("emotion detection"),
        KeywordRule("emotion recognition"),
        KeywordRule("emotion inference"),
        KeywordRule("affect recognition"),
        KeywordRule("facial emotion"),
    ]),
    # --- Article 50 transparency signals ---
    ("has_ai_disclosure", [
        KeywordRule("ai disclosure"),
        KeywordRule("powered by ai"),
        KeywordRule("ai-generated"),
        KeywordRule("generated by ai"),
        KeywordRule("this is an ai"),
        KeywordRule("chatbot"),
        KeywordRule("ai assistant"),
    ]),
    ("has_synthetic_content_marking", [
        KeywordRule("watermark"),
        KeywordRule("synthetic content"),
        KeywordRule("ai-generated content"),
        KeywordRule("machine-generated"),
        KeywordRule("content provenance"),
        KeywordRule("c2pa"),
    ]),
    ("has_provider_identification", [
        KeywordRule("provider name", require_doc_context=True),
        KeywordRule("contact information", require_doc_context=True),
        KeywordRule("developed by", require_doc_context=True),
        KeywordRule("maintained by", require_doc_context=True),
        KeywordRule("version:", require_doc_context=True),
    ]),
]

# Content patterns for TrainingDataStats sub-fields (unchanged)
TRAINING_DATA_CONTENT_RULES: list[tuple[str, list[str]]] = [
    ("provenance_documented", ["data source", "provenance"]),
    ("preprocessing_documented", ["preprocessing", "feature engineer"]),
]

# Content patterns for quality_metrics_logged (Phase 1C replacement)
QUALITY_METRICS_KEYWORDS: list[str] = [
    "data quality metric", "quality score", "completeness rate",
    "data quality", "quality metrics",
]

# AI API key variable names — presence in .env.example signals AI usage
ENV_AI_KEY_PATTERNS: list[str] = [
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "COHERE_API_KEY",
    "GOOGLE_AI_KEY", "HUGGINGFACE_TOKEN", "REPLICATE_API_TOKEN",
    "TOGETHER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
]


def _collapse_directory_matches(matches: list[str], max_specific: int = 3) -> list[str]:
    """Collapse large directory matches into summary entries.

    If many files share a common directory prefix, replace them with
    a single "directory/ (N files)" entry. Specific files (no common
    directory or small count) are kept as-is.
    """
    if len(matches) <= max_specific:
        return matches

    # Group by top-level directory
    from collections import Counter
    dirs: Counter[str] = Counter()
    specific: list[str] = []
    for path in matches:
        if "/" in path:
            top_dir = path.split("/")[0]
            dirs[top_dir] += 1
        else:
            specific.append(path)

    result: list[str] = list(specific)
    for dir_name, count in dirs.most_common():
        if count > max_specific:
            result.append(f"{dir_name}/ ({count} files)")
        else:
            # Keep individual files for small directories
            result.extend(p for p in matches if p.startswith(dir_name + "/"))

    return result[:max_specific + len(dirs)] if result else matches[:max_specific]


def check_file_tree_flags(
    file_paths: list[str],
) -> tuple[dict[str, bool], dict[str, list[str]]]:
    """Match file paths against compliance patterns.

    Args:
        file_paths: list of repo-relative paths (e.g. "tests/test_model.py")

    Returns:
        Tuple of (flags, matched_paths):
        - flags: dict with ScannerOutput field names → bool
        - matched_paths: dict with field names → list of actual file paths that matched
        Also includes internal flags: ``performance_metrics_present``,
        ``bias_analysis_found``, ``user_instructions_found``.
    """
    original_map = {p.lower(): p for p in file_paths}
    lowered = list(original_map.keys())

    flags: dict[str, bool] = {}
    matched_paths: dict[str, list[str]] = {}

    for field_name, patterns in FILE_TREE_RULES:
        matches = [
            original_map[fp]
            for fp in lowered
            for pat in patterns
            if fnmatch(fp, pat.lower())
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_matches = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                unique_matches.append(m)
        flags[field_name] = flags.get(field_name, False) or bool(unique_matches)
        if unique_matches:
            collapsed = _collapse_directory_matches(unique_matches)
            matched_paths.setdefault(field_name, []).extend(collapsed)

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

    return flags, matched_paths


def extract_content_flags(
    contents: dict[str, str],
) -> tuple[dict[str, bool | dict[str, bool]], dict[str, list[str]]]:
    """Keyword-match file contents for compliance signals.

    Phase 2 overhaul: uses KeywordRule with word boundaries and per-file
    context awareness to reduce false positives.

    Args:
        contents: dict mapping filename → file content text.

    Returns:
        Tuple of (flags, matched_paths):
        - flags: dict with ScannerOutput field names as keys.
          Also includes ``training_data_sub`` dict with sub-field bools.
        - matched_paths: dict with field names → list of filenames that matched
    """
    flags: dict[str, bool | dict[str, bool]] = {}
    matched_paths: dict[str, list[str]] = {}

    for field_name, rules in CONTENT_RULES:
        matching_files = []
        for rule in rules:
            for filename, content in contents.items():
                lower_content = content.lower()
                if rule.require_doc_context and _is_source_code_file(filename):
                    continue
                if _matches_keyword_in_text(rule, lower_content):
                    if filename not in matching_files:
                        matching_files.append(filename)
        if matching_files:
            flags[field_name] = True
            new_files = [f for f in matching_files if f not in matched_paths.get(field_name, [])]
            collapsed = _collapse_directory_matches(new_files)
            matched_paths.setdefault(field_name, []).extend(collapsed)
        else:
            flags[field_name] = bool(flags.get(field_name, False))

    # Training data sub-field signals (simple substring — low FP risk)
    combined = "\n".join(contents.values()).lower()
    training_sub: dict[str, bool] = {}
    for sub_field, keywords in TRAINING_DATA_CONTENT_RULES:
        training_sub[sub_field] = any(kw in combined for kw in keywords)
    flags["training_data_sub"] = training_sub

    # Quality metrics signal (Phase 1C — real content match)
    flags["quality_metrics_found"] = any(
        kw in combined for kw in QUALITY_METRICS_KEYWORDS
    )

    # Adversarial testing signal (unchanged — low FP risk in doc context)
    flags["adversarial_tested"] = any(
        kw in combined for kw in ["adversarial", "robustness test"]
    )

    # AI API key detection (from .env.example or docker-compose.yml)
    upper_combined = "\n".join(contents.values())
    flags["ai_api_keys_found"] = any(
        key in upper_combined for key in ENV_AI_KEY_PATTERNS
    )

    return flags, matched_paths


# ---------------------------------------------------------------------------
# Section-based document validation (ported from Systima Comply, Apache 2.0)
# ---------------------------------------------------------------------------

# Required section keywords per document type.
# A document "has" a section if any of the keywords appear (case-insensitive).
DOC_SECTION_REQUIREMENTS: dict[str, list[str]] = {
    "risk_assessment": [
        "risk identification", "risk estimation", "risk evaluation",
        "risk mitigation", "residual risk",
    ],
    "data_documentation": [
        "data sources", "data quality", "bias",
    ],
    "model_card": [
        "intended use", "limitations", "performance", "training data",
    ],
    "transparency": [
        "capabilities", "limitations", "intended use",
    ],
    "human_oversight": [
        "oversight", "intervention", "override",
    ],
}

# Map filename patterns to doc types
_DOC_TYPE_PATTERNS: list[tuple[str, list[str]]] = [
    ("risk_assessment", ["risk_assessment", "risk-assessment", "risk_management", "risk-management"]),
    ("data_documentation", ["data_card", "data-card", "dataset_card", "dataset-card", "datasheet"]),
    ("model_card", ["model_card", "model-card"]),
    ("transparency", ["transparency"]),
    ("human_oversight", ["human_oversight", "human-oversight"]),
]


def _classify_doc_type(filename: str) -> str | None:
    """Classify a filename into a doc_type, or None if unrecognized."""
    lower = filename.lower()
    for doc_type, patterns in _DOC_TYPE_PATTERNS:
        if any(pat in lower for pat in patterns):
            return doc_type
    return None


def validate_doc_sections(filename: str, content: str) -> DocValidation | None:
    """Check if a compliance doc contains required section keywords.

    Args:
        filename: The file name/path of the document.
        content: The document's text content.

    Returns:
        DocValidation with completeness score, or None if the filename
        doesn't match a known doc type.
    """
    doc_type = _classify_doc_type(filename)
    if doc_type is None:
        return None

    required = DOC_SECTION_REQUIREMENTS.get(doc_type, [])
    if not required:
        return None

    lower_content = content.lower()
    found = [section for section in required if section in lower_content]
    missing = [section for section in required if section not in lower_content]

    completeness = len(found) / len(required) if required else 0.0

    return DocValidation(
        doc_type=doc_type,
        sections_found=found,
        sections_missing=missing,
        completeness_score=round(completeness, 2),
    )
