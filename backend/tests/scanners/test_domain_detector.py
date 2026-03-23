"""Tests for domain_detector — Annex III category inference from keywords."""

from __future__ import annotations

from app.scanners.domain_detector import detect_domains


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
