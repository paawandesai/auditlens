# Scanning patterns adapted from Systima Comply (Apache 2.0)
# https://github.com/systima-ai/comply
"""Annex III domain detection from content keywords.

Pure function: scans text (README, docs) for domain-specific keywords
and infers which EU AI Act Annex III categories apply. Zero API calls —
operates on already-fetched content.

Scoring: sum of matched keyword weights ≥ threshold = domain detected.
Strong multi-word phrases (weight 2.0) can trigger alone.
Contextual boosting: if AI frameworks detected, threshold drops to 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.scanner import DetectedDomain

# ---------------------------------------------------------------------------
# Weighted keyword data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightedKeyword:
    """A keyword with a weight indicating signal strength.

    Strong signals (weight 2.0): Multi-word phrases that unambiguously
    indicate a specific domain (e.g., "candidate screening").
    Weak signals (weight 1.0): Generic words that could appear in
    non-domain contexts (e.g., "candidate").
    """

    phrase: str
    weight: float = 1.0


# ---------------------------------------------------------------------------
# Detection threshold
# ---------------------------------------------------------------------------
BASE_THRESHOLD = 2.0
CONTEXTUAL_THRESHOLD = 1.0  # When AI frameworks are detected
CONTEXTUAL_CONFIDENCE_CAP = 0.5  # Max confidence for contextual-boost detections

# ---------------------------------------------------------------------------
# Annex III category keyword lists (weighted)
# ---------------------------------------------------------------------------
# Each entry: (domain_name, annex_iii_category, weighted_keyword_list)

DOMAIN_KEYWORDS: list[tuple[str, str, list[WeightedKeyword]]] = [
    # Category 1: Biometric identification
    ("biometrics", "1a", [
        WeightedKeyword("facial recognition", 2.0),
        WeightedKeyword("face recognition", 2.0),
        WeightedKeyword("emotion recognition", 2.0),
        WeightedKeyword("emotion detection", 2.0),
        WeightedKeyword("face identification", 2.0),
        WeightedKeyword("biometric", 1.0),
        WeightedKeyword("fingerprint", 1.0),
        WeightedKeyword("iris scan", 1.0),
        WeightedKeyword("voice recognition", 1.0),
        WeightedKeyword("gait analysis", 1.0),
        WeightedKeyword("face detection", 1.0),
    ]),
    # Category 2: Critical infrastructure
    ("critical_infrastructure", "2", [
        WeightedKeyword("critical infrastructure", 2.0),
        WeightedKeyword("power grid", 2.0),
        WeightedKeyword("energy grid", 2.0),
        WeightedKeyword("water treatment", 2.0),
        WeightedKeyword("air traffic", 2.0),
        WeightedKeyword("traffic management", 2.0),
        WeightedKeyword("water supply", 1.0),
        WeightedKeyword("gas supply", 1.0),
        WeightedKeyword("electricity", 1.0),
        WeightedKeyword("railway", 1.0),
    ]),
    # Category 3a: Education — access and admission
    ("education_access", "3a", [
        WeightedKeyword("student admission", 2.0),
        WeightedKeyword("school admission", 2.0),
        WeightedKeyword("university admission", 2.0),
        WeightedKeyword("academic admission", 2.0),
        WeightedKeyword("enrollment decision", 2.0),
        WeightedKeyword("student selection", 2.0),
        WeightedKeyword("educational institution", 1.0),
        WeightedKeyword("student enrollment", 1.0),
    ]),
    # Category 3b: Education — assessment
    ("education_assessment", "3b", [
        WeightedKeyword("automated grading", 2.0),
        WeightedKeyword("exam scoring", 2.0),
        WeightedKeyword("plagiarism detection", 2.0),
        WeightedKeyword("student assessment", 1.0),
        WeightedKeyword("grading system", 1.0),
        WeightedKeyword("student evaluation", 1.0),
        WeightedKeyword("academic performance", 1.0),
        WeightedKeyword("learning outcome", 1.0),
        WeightedKeyword("proctoring", 1.0),
    ]),
    # Category 4a: Employment — recruitment (PRIORITY WEDGE)
    ("employment_recruitment", "4a", [
        # Strong signals: unambiguous multi-word phrases
        WeightedKeyword("candidate screening", 2.0),
        WeightedKeyword("resume screening", 2.0),
        WeightedKeyword("cv screening", 2.0),
        WeightedKeyword("applicant tracking", 2.0),
        WeightedKeyword("talent acquisition", 2.0),
        WeightedKeyword("interview scoring", 2.0),
        WeightedKeyword("hiring pipeline", 2.0),
        WeightedKeyword("recruitment ai", 2.0),
        WeightedKeyword("hiring ai", 2.0),
        WeightedKeyword("candidate ranking", 2.0),
        WeightedKeyword("candidate selection", 2.0),
        WeightedKeyword("job matching", 2.0),
        # Weak signals: could appear in non-employment contexts
        WeightedKeyword("recruitment", 1.0),
        WeightedKeyword("hiring", 1.0),
        WeightedKeyword("candidate", 1.0),
        WeightedKeyword("job applicant", 1.0),
        WeightedKeyword("job application", 1.0),
    ]),
    # Category 4b: Employment — management decisions
    ("employment_management", "4b", [
        WeightedKeyword("employee evaluation", 2.0),
        WeightedKeyword("employee assessment", 2.0),
        WeightedKeyword("performance monitoring", 2.0),
        WeightedKeyword("performance review", 2.0),
        WeightedKeyword("workforce management", 2.0),
        WeightedKeyword("promotion", 1.0),
        WeightedKeyword("termination", 1.0),
        WeightedKeyword("task allocation", 1.0),
        WeightedKeyword("disciplinary", 1.0),
    ]),
    # Category 4c: Employment — worker monitoring
    ("employment_monitoring", "4c", [
        WeightedKeyword("worker monitoring", 2.0),
        WeightedKeyword("employee monitoring", 2.0),
        WeightedKeyword("workplace surveillance", 2.0),
        WeightedKeyword("productivity tracking", 2.0),
        WeightedKeyword("keystroke logging", 2.0),
        WeightedKeyword("screen monitoring", 2.0),
        WeightedKeyword("attendance monitoring", 2.0),
        WeightedKeyword("time tracking", 1.0),
    ]),
    # Category 5a: Public benefits
    ("public_benefits", "5a", [
        WeightedKeyword("benefit eligibility", 2.0),
        WeightedKeyword("social assistance", 2.0),
        WeightedKeyword("public benefit", 1.0),
        WeightedKeyword("social benefit", 1.0),
        WeightedKeyword("welfare", 1.0),
        WeightedKeyword("social security", 1.0),
        WeightedKeyword("unemployment benefit", 1.0),
        WeightedKeyword("disability benefit", 1.0),
    ]),
    # Category 5b: Creditworthiness
    ("creditworthiness", "5b", [
        WeightedKeyword("credit scoring", 2.0),
        WeightedKeyword("credit risk", 2.0),
        WeightedKeyword("credit assessment", 2.0),
        WeightedKeyword("loan approval", 2.0),
        WeightedKeyword("lending decision", 2.0),
        WeightedKeyword("creditworthiness", 1.0),
        WeightedKeyword("credit decision", 1.0),
        WeightedKeyword("loan application", 1.0),
        WeightedKeyword("credit rating", 1.0),
        WeightedKeyword("financial scoring", 1.0),
    ]),
    # Category 5c: Insurance
    ("insurance", "5c", [
        WeightedKeyword("insurance pricing", 2.0),
        WeightedKeyword("insurance underwriting", 2.0),
        WeightedKeyword("insurance risk", 2.0),
        WeightedKeyword("insurance premium", 2.0),
        WeightedKeyword("actuarial", 1.0),
        WeightedKeyword("insurance claim", 1.0),
        WeightedKeyword("risk premium", 1.0),
        WeightedKeyword("health insurance", 1.0),
        WeightedKeyword("life insurance", 1.0),
    ]),
    # Category 6d: Law enforcement
    ("law_enforcement", "6d", [
        WeightedKeyword("predictive policing", 2.0),
        WeightedKeyword("crime prediction", 2.0),
        WeightedKeyword("law enforcement", 2.0),
        WeightedKeyword("lie detection", 2.0),
        WeightedKeyword("police", 1.0),
        WeightedKeyword("criminal", 1.0),
        WeightedKeyword("suspect", 1.0),
        WeightedKeyword("recidivism", 1.0),
        WeightedKeyword("parole", 1.0),
        WeightedKeyword("probation", 1.0),
        WeightedKeyword("polygraph", 1.0),
    ]),
    # Category 7b: Migration and border
    ("migration", "7b", [
        WeightedKeyword("border control", 2.0),
        WeightedKeyword("passport verification", 2.0),
        WeightedKeyword("travel document", 2.0),
        WeightedKeyword("migration", 1.0),
        WeightedKeyword("asylum", 1.0),
        WeightedKeyword("visa", 1.0),
        WeightedKeyword("immigration", 1.0),
        WeightedKeyword("refugee", 1.0),
    ]),
    # Category 8a: Justice
    ("justice", "8a", [
        WeightedKeyword("court decision", 2.0),
        WeightedKeyword("bail decision", 2.0),
        WeightedKeyword("legal decision", 2.0),
        WeightedKeyword("sentencing", 1.0),
        WeightedKeyword("judicial", 1.0),
        WeightedKeyword("justice system", 1.0),
        WeightedKeyword("pardon", 1.0),
        WeightedKeyword("case outcome", 1.0),
    ]),
]


def detect_domains(
    text: str,
    *,
    has_ai_frameworks: bool = False,
) -> list[DetectedDomain]:
    """Detect Annex III domains from combined content text.

    Args:
        text: Combined text from README, docs, and other content files.
        has_ai_frameworks: Whether AI/ML frameworks were detected in the repo.
            When True, the detection threshold is lowered (contextual boosting).

    Returns:
        List of detected domains where total keyword weight ≥ threshold.
    """
    if not text:
        return []

    lower_text = text.lower()
    threshold = CONTEXTUAL_THRESHOLD if has_ai_frameworks else BASE_THRESHOLD
    results: list[DetectedDomain] = []

    for domain, category, keywords in DOMAIN_KEYWORDS:
        matched: list[str] = []
        total_weight = 0.0

        for kw in keywords:
            if kw.phrase in lower_text:
                matched.append(kw.phrase)
                total_weight += kw.weight

        if total_weight >= threshold and matched:
            # Confidence scales with total weight
            confidence = min(0.3 + 0.15 * total_weight, 1.0)

            # Cap confidence for contextual-boost-only detections
            # (weight crossed contextual threshold but not base threshold)
            if total_weight < BASE_THRESHOLD:
                confidence = min(confidence, CONTEXTUAL_CONFIDENCE_CAP)

            results.append(DetectedDomain(
                domain=domain,
                annex_iii_category=category,
                confidence=confidence,
                matched_keywords=matched,
            ))

    return results
