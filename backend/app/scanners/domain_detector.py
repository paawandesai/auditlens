# Scanning patterns adapted from Systima Comply (Apache 2.0)
# https://github.com/systima-ai/comply
"""Annex III domain detection from content keywords.

Pure function: scans text (README, docs) for domain-specific keywords
and infers which EU AI Act Annex III categories apply. Zero API calls —
operates on already-fetched content.

Rule: ≥2 keyword matches = domain detected (same threshold as Comply).
"""

from __future__ import annotations

from app.schemas.scanner import DetectedDomain

# ---------------------------------------------------------------------------
# Annex III category keyword lists
# ---------------------------------------------------------------------------
# Each entry: (domain_name, annex_iii_category, keyword_list)
# Keywords are matched case-insensitively as substrings in the combined text.

DOMAIN_KEYWORDS: list[tuple[str, str, list[str]]] = [
    # Category 1: Biometric identification
    ("biometrics", "1a", [
        "biometric", "facial recognition", "face recognition", "fingerprint",
        "iris scan", "voice recognition", "gait analysis", "emotion recognition",
        "emotion detection", "face detection", "face identification",
    ]),
    # Category 2: Critical infrastructure
    ("critical_infrastructure", "2", [
        "critical infrastructure", "power grid", "energy grid", "water supply",
        "gas supply", "electricity", "traffic management", "air traffic",
        "railway", "water treatment",
    ]),
    # Category 3a: Education — access and admission
    ("education_access", "3a", [
        "student admission", "school admission", "university admission",
        "educational institution", "student selection", "academic admission",
        "enrollment decision", "student enrollment",
    ]),
    # Category 3b: Education — assessment
    ("education_assessment", "3b", [
        "student assessment", "exam scoring", "grading system", "automated grading",
        "student evaluation", "academic performance", "learning outcome",
        "proctoring", "plagiarism detection",
    ]),
    # Category 4a: Employment — recruitment
    ("employment_recruitment", "4a", [
        "recruitment", "hiring", "candidate", "job applicant", "resume screening",
        "cv screening", "applicant tracking", "talent acquisition",
        "job application", "interview scoring",
    ]),
    # Category 4b: Employment — management decisions
    ("employment_management", "4b", [
        "promotion", "termination", "task allocation", "performance monitoring",
        "employee evaluation", "workforce management", "performance review",
        "disciplinary", "employee assessment",
    ]),
    # Category 4c: Employment — worker monitoring
    ("employment_monitoring", "4c", [
        "worker monitoring", "employee monitoring", "workplace surveillance",
        "productivity tracking", "keystroke logging", "screen monitoring",
        "time tracking", "attendance monitoring",
    ]),
    # Category 5a: Public benefits
    ("public_benefits", "5a", [
        "public benefit", "social benefit", "welfare", "social assistance",
        "benefit eligibility", "social security", "unemployment benefit",
        "disability benefit",
    ]),
    # Category 5b: Creditworthiness
    ("creditworthiness", "5b", [
        "credit scoring", "creditworthiness", "credit risk", "credit assessment",
        "credit decision", "loan approval", "loan application", "credit rating",
        "financial scoring", "lending decision",
    ]),
    # Category 5c: Insurance
    ("insurance", "5c", [
        "insurance pricing", "insurance risk", "insurance underwriting",
        "actuarial", "insurance claim", "insurance premium", "risk premium",
        "health insurance", "life insurance",
    ]),
    # Category 6d: Law enforcement
    ("law_enforcement", "6d", [
        "law enforcement", "police", "crime prediction", "predictive policing",
        "criminal", "suspect", "recidivism", "parole", "probation",
        "lie detection", "polygraph",
    ]),
    # Category 7b: Migration and border
    ("migration", "7b", [
        "migration", "asylum", "border control", "visa", "immigration",
        "refugee", "travel document", "passport verification",
    ]),
    # Category 8a: Justice
    ("justice", "8a", [
        "sentencing", "judicial", "court decision", "legal decision",
        "justice system", "bail decision", "pardon", "case outcome",
    ]),
]


def detect_domains(text: str) -> list[DetectedDomain]:
    """Detect Annex III domains from combined content text.

    Args:
        text: Combined text from README, docs, and other content files.

    Returns:
        List of detected domains where ≥2 keywords matched.
    """
    if not text:
        return []

    lower_text = text.lower()
    results: list[DetectedDomain] = []

    for domain, category, keywords in DOMAIN_KEYWORDS:
        matched = [kw for kw in keywords if kw in lower_text]
        if len(matched) >= 2:
            # Confidence scales with number of matches (cap at 1.0)
            confidence = min(0.5 + 0.1 * len(matched), 1.0)
            results.append(DetectedDomain(
                domain=domain,
                annex_iii_category=category,
                confidence=confidence,
                matched_keywords=matched,
            ))

    return results
