"""Risk classifier — deterministic three-signal weighted scoring.

Classifies a ScannerOutput into a risk level using:
  Signal A (0.40): Framework HR-relevance scores
  Signal B (0.35): Detected domains from domain_detector
  Signal C (0.25): Data subject inference from domain categories

No LLM. Reproducible. Auditable.
"""

from __future__ import annotations

from app.schemas.scanner import (
    RiskClassification,
    ScannerOutput,
)

# Domain categories that imply specific data subjects
_DOMAIN_DATA_SUBJECTS: dict[str, float] = {
    "4a": 0.95,  # Recruitment → candidates
    "4b": 0.90,  # Promotion/termination → employees
    "4c": 0.90,  # Worker monitoring → employees
    "3": 0.60,   # Education → students
    "5": 0.50,   # Essential services → citizens
    "1": 0.70,   # Biometrics → individuals
}


class RiskClassifier:
    """Deterministic risk classification using three-signal scoring."""

    FRAMEWORK_WEIGHT = 0.40
    DOMAIN_WEIGHT = 0.35
    DATA_SUBJECT_WEIGHT = 0.25

    HIGH_RISK_THRESHOLD = 0.65
    LIMITED_RISK_THRESHOLD = 0.35
    MINIMAL_THRESHOLD = 0.10

    def classify(self, scanner_output: ScannerOutput) -> RiskClassification:
        """Classify risk from a fully-populated ScannerOutput."""
        frameworks = scanner_output.detected_frameworks
        domains = scanner_output.detected_domains

        if not frameworks and not domains:
            return RiskClassification(
                risk_level="UNDETERMINED",
                risk_score=0,
                confidence=0.0,
                evidence=[{
                    "signal_type": "none",
                    "detail": "No frameworks or domains detected",
                    "score": 0.0,
                    "weight": 0.0,
                }],
            )

        # Signal A: Framework HR-relevance
        fw_score, fw_evidence = self._score_frameworks(scanner_output)

        # Signal B: Domain detection
        domain_score, domain_evidence, best_category = self._score_domains(scanner_output)

        # Signal C: Data subject inference (derived from domains)
        ds_score, ds_evidence = self._score_data_subjects(scanner_output)

        # Weighted composite
        composite = (
            fw_score * self.FRAMEWORK_WEIGHT
            + domain_score * self.DOMAIN_WEIGHT
            + ds_score * self.DATA_SUBJECT_WEIGHT
        )

        risk_level = self._score_to_level(composite)
        risk_score = round(composite * 100)

        # Only assign category if risk is HIGH or LIMITED
        annex_category = best_category if risk_level in ("HIGH", "LIMITED") else None

        evidence = fw_evidence + domain_evidence + ds_evidence

        return RiskClassification(
            risk_level=risk_level,
            risk_score=risk_score,
            annex_iii_category=annex_category,
            confidence=min(composite + 0.1, 1.0),
            evidence=evidence,
        )

    def _score_frameworks(
        self, scanner_output: ScannerOutput,
    ) -> tuple[float, list[dict]]:
        """Signal A: max HR-relevance score from detected frameworks."""
        frameworks = scanner_output.detected_frameworks
        if not frameworks:
            return 0.0, [{
                "signal_type": "framework",
                "detail": "No AI/ML frameworks detected",
                "score": 0.0,
                "weight": self.FRAMEWORK_WEIGHT,
            }]

        max_hr = max(f.hr_relevance_score for f in frameworks)
        count_boost = min(len(frameworks) * 0.05, 0.2)
        score = min(max_hr + count_boost, 1.0)

        evidence = [{
            "signal_type": "framework",
            "detail": f"{f.name} (HR relevance: {f.hr_relevance_score:.2f})",
            "score": score,
            "weight": self.FRAMEWORK_WEIGHT,
        } for f in frameworks]

        return score, evidence

    def _score_domains(
        self, scanner_output: ScannerOutput,
    ) -> tuple[float, list[dict], str | None]:
        """Signal B: highest-confidence detected domain."""
        domains = scanner_output.detected_domains
        if not domains:
            return 0.0, [{
                "signal_type": "domain",
                "detail": "No Annex III domains detected",
                "score": 0.0,
                "weight": self.DOMAIN_WEIGHT,
            }], None

        best = max(domains, key=lambda d: d.confidence)
        score = best.confidence

        evidence = [{
            "signal_type": "domain",
            "detail": (
                f"{d.domain} (category {d.annex_iii_category}, "
                f"confidence: {d.confidence:.0%}, "
                f"keywords: {', '.join(d.matched_keywords[:3])})"
            ),
            "score": d.confidence,
            "weight": self.DOMAIN_WEIGHT,
        } for d in domains]

        return score, evidence, best.annex_iii_category

    def _score_data_subjects(
        self, scanner_output: ScannerOutput,
    ) -> tuple[float, list[dict]]:
        """Signal C: data subject relevance inferred from domain categories."""
        domains = scanner_output.detected_domains
        if not domains:
            return 0.0, [{
                "signal_type": "data_subject",
                "detail": "No domains to infer data subjects from",
                "score": 0.0,
                "weight": self.DATA_SUBJECT_WEIGHT,
            }]

        best_relevance = 0.0
        evidence: list[dict] = []
        for d in domains:
            relevance = _DOMAIN_DATA_SUBJECTS.get(d.annex_iii_category, 0.2)
            weighted = relevance * d.confidence
            if weighted > best_relevance:
                best_relevance = weighted
            evidence.append({
                "signal_type": "data_subject",
                "detail": f"Category {d.annex_iii_category} implies affected persons (relevance: {relevance:.2f})",
                "score": weighted,
                "weight": self.DATA_SUBJECT_WEIGHT,
            })

        return best_relevance, evidence

    def _score_to_level(self, score: float) -> str:
        """Convert composite score to risk level string."""
        if score >= self.HIGH_RISK_THRESHOLD:
            return "HIGH"
        if score >= self.LIMITED_RISK_THRESHOLD:
            return "LIMITED"
        if score >= self.MINIMAL_THRESHOLD:
            return "MINIMAL"
        return "UNDETERMINED"
