"""Tests for domain_detector — Annex III category inference from keywords."""

from __future__ import annotations

from app.scanners.domain_detector import detect_domains, WeightedKeyword


class TestDetectDomains:
    """Tests for detect_domains()."""

    def test_empty_text_no_domains(self):
        assert detect_domains("") == []

    def test_irrelevant_text_no_domains(self):
        text = "This is a weather forecasting application that predicts rain."
        assert detect_domains(text) == []

    def test_single_keyword_not_enough(self):
        """A single keyword should NOT trigger detection (threshold is 2)."""
        text = "Our system handles recruitment."
        assert detect_domains(text) == []

    def test_employment_recruitment_detected(self):
        text = "AI-powered recruitment system for screening job applicants and resume screening."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_recruitment" in names
        match = next(d for d in domains if d.domain == "employment_recruitment")
        assert match.annex_iii_category == "4a"
        assert len(match.matched_keywords) >= 2

    def test_employment_management_detected(self):
        text = "System for employee evaluation and performance monitoring in the workplace."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_management" in names
        match = next(d for d in domains if d.domain == "employment_management")
        assert match.annex_iii_category == "4b"

    def test_employment_monitoring_detected(self):
        text = "Productivity tracking and employee monitoring solution for the office."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_monitoring" in names

    def test_creditworthiness_detected(self):
        text = "Credit scoring model for loan approval and credit risk assessment."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "creditworthiness" in names
        match = next(d for d in domains if d.domain == "creditworthiness")
        assert match.annex_iii_category == "5b"

    def test_biometrics_detected(self):
        text = "Facial recognition system with emotion detection capabilities."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "biometrics" in names
        match = next(d for d in domains if d.domain == "biometrics")
        assert match.annex_iii_category == "1a"

    def test_education_access_detected(self):
        text = "AI for student admission decisions at educational institution level."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "education_access" in names

    def test_education_assessment_detected(self):
        text = "Automated grading and student assessment platform."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "education_assessment" in names

    def test_law_enforcement_detected(self):
        text = "Crime prediction and predictive policing algorithm."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "law_enforcement" in names

    def test_multiple_domains_detected(self):
        text = (
            "Our platform handles recruitment and resume screening for hiring. "
            "It also includes credit scoring and loan approval features."
        )
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_recruitment" in names
        assert "creditworthiness" in names
        assert len(domains) >= 2

    def test_confidence_scales_with_matches(self):
        text = (
            "recruitment hiring candidate job applicant resume screening "
            "applicant tracking talent acquisition"
        )
        domains = detect_domains(text)
        match = next(d for d in domains if d.domain == "employment_recruitment")
        # More keywords → higher confidence
        assert match.confidence > 0.5

    def test_confidence_capped_at_one(self):
        """Even with many matches, confidence should not exceed 1.0."""
        text = (
            "recruitment hiring candidate job applicant resume screening "
            "cv screening applicant tracking talent acquisition job application "
            "interview scoring"
        )
        domains = detect_domains(text)
        match = next(d for d in domains if d.domain == "employment_recruitment")
        assert match.confidence <= 1.0

    def test_case_insensitive(self):
        text = "FACIAL RECOGNITION and EMOTION DETECTION system"
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "biometrics" in names

    def test_insurance_detected(self):
        text = "Insurance pricing model with actuarial analysis for risk premium."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "insurance" in names
        match = next(d for d in domains if d.domain == "insurance")
        assert match.annex_iii_category == "5c"


class TestWeightedScoring:
    """Tests for weighted keyword scoring (replaces flat count threshold)."""

    def test_single_strong_phrase_triggers_detection(self):
        """A strong multi-word phrase (weight 2.0) should trigger detection alone."""
        text = "ML-powered candidate screening tool for enterprises."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_recruitment" in names
        match = next(d for d in domains if d.domain == "employment_recruitment")
        assert match.annex_iii_category == "4a"

    def test_single_weak_keyword_does_not_trigger(self):
        """A single weak keyword (weight 1.0) must NOT trigger without context."""
        text = "Our system handles recruitment."
        domains = detect_domains(text)
        assert domains == []

    def test_weak_keyword_plus_framework_context_triggers(self):
        """With AI frameworks detected, a single weak keyword should trigger at low confidence."""
        text = "Our system handles recruitment."
        domains = detect_domains(text, has_ai_frameworks=True)
        names = [d.domain for d in domains]
        assert "employment_recruitment" in names
        match = next(d for d in domains if d.domain == "employment_recruitment")
        assert match.confidence <= 0.5, "Contextual boost should cap confidence at 0.5"

    def test_two_weak_keywords_still_works(self):
        """Backward compat: 2 weak keywords (1.0 + 1.0 = 2.0) still trigger."""
        text = "Our recruitment platform helps hiring managers."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_recruitment" in names

    def test_strong_phrase_higher_confidence_than_two_weak(self):
        """A strong phrase should produce higher confidence than two weak keywords."""
        strong_text = "Resume screening and candidate screening pipeline."
        weak_text = "Recruitment and hiring process."
        strong_domains = detect_domains(strong_text)
        weak_domains = detect_domains(weak_text)
        strong_match = next(d for d in strong_domains if d.domain == "employment_recruitment")
        weak_match = next(d for d in weak_domains if d.domain == "employment_recruitment")
        assert strong_match.confidence >= weak_match.confidence

    def test_contextual_boost_no_frameworks_no_trigger(self):
        """Without has_ai_frameworks=True, single weak keyword still doesn't trigger."""
        text = "Our system handles recruitment."
        domains = detect_domains(text, has_ai_frameworks=False)
        assert domains == []

    def test_hiring_pipeline_strong_phrase(self):
        """'hiring pipeline' as a strong phrase should trigger alone."""
        text = "We built a hiring pipeline using machine learning."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_recruitment" in names

    def test_weighted_keyword_dataclass(self):
        """WeightedKeyword should be a frozen dataclass with defaults."""
        kw = WeightedKeyword("test phrase")
        assert kw.phrase == "test phrase"
        assert kw.weight == 1.0
        strong = WeightedKeyword("strong phrase", weight=2.0)
        assert strong.weight == 2.0

    def test_4b_strong_phrases(self):
        """Category 4b strong phrases should trigger detection alone."""
        text = "Our employee assessment system uses ML for performance review."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_management" in names

    def test_4c_strong_phrases(self):
        """Category 4c strong phrases should trigger detection alone."""
        text = "AI-driven workplace surveillance system for offices."
        domains = detect_domains(text)
        names = [d.domain for d in domains]
        assert "employment_monitoring" in names
