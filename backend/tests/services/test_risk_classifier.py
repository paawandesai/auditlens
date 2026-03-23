"""Tests for risk classifier — three-signal weighted scoring."""

from __future__ import annotations

import pytest

from app.schemas.scanner import (
    DetectedDomain,
    DetectedFramework,
    RiskClassification,
    ScannerOutput,
)
from app.services.risk_classifier import RiskClassifier


def _make_output(
    frameworks: list[DetectedFramework] | None = None,
    domains: list[DetectedDomain] | None = None,
) -> ScannerOutput:
    return ScannerOutput(
        repo_url="https://github.com/test/repo",
        detected_frameworks=frameworks or [],
        detected_domains=domains or [],
    )


class TestRiskClassifierEmpty:
    """Empty / minimal input → graceful UNDETERMINED."""

    def test_empty_scanner_output(self):
        result = RiskClassifier().classify(_make_output())
        assert result.risk_level == "UNDETERMINED"
        assert result.risk_score == 0
        assert result.confidence >= 0.0

    def test_no_frameworks_no_domains(self):
        result = RiskClassifier().classify(_make_output(frameworks=[], domains=[]))
        assert result.risk_level == "UNDETERMINED"

    def test_evidence_populated_even_for_undetermined(self):
        result = RiskClassifier().classify(_make_output())
        assert isinstance(result.evidence, list)


class TestRiskClassifierHighRisk:
    """High HR-relevance frameworks + employment domain → HIGH risk."""

    def test_high_hr_frameworks_with_employment_domain(self):
        frameworks = [
            DetectedFramework(name="scikit-learn", confidence=0.95, hr_relevance_score=0.8),
            DetectedFramework(name="aif360", confidence=0.9, hr_relevance_score=0.95),
        ]
        domains = [
            DetectedDomain(
                domain="employment",
                annex_iii_category="4a",
                confidence=0.9,
                matched_keywords=["hiring", "candidate"],
            ),
        ]
        result = RiskClassifier().classify(_make_output(frameworks, domains))
        assert result.risk_level == "HIGH"
        assert result.risk_score >= 65
        assert result.annex_iii_category == "4a"

    def test_single_high_framework_with_domain(self):
        frameworks = [
            DetectedFramework(name="scikit-learn", confidence=0.95, hr_relevance_score=0.85),
        ]
        domains = [
            DetectedDomain(
                domain="employment",
                annex_iii_category="4b",
                confidence=0.85,
                matched_keywords=["employee", "performance"],
            ),
        ]
        result = RiskClassifier().classify(_make_output(frameworks, domains))
        assert result.risk_level == "HIGH"
        assert result.annex_iii_category == "4b"


class TestRiskClassifierMinimal:
    """Low-relevance frameworks + no domain → MINIMAL."""

    def test_low_relevance_no_domain(self):
        frameworks = [
            DetectedFramework(name="numpy", confidence=0.95, hr_relevance_score=0.1),
        ]
        result = RiskClassifier().classify(_make_output(frameworks=frameworks))
        assert result.risk_level in ("MINIMAL", "UNDETERMINED")
        assert result.risk_score < 35

    def test_data_only_frameworks(self):
        frameworks = [
            DetectedFramework(name="pandas", confidence=0.95, hr_relevance_score=0.05),
            DetectedFramework(name="numpy", confidence=0.95, hr_relevance_score=0.05),
        ]
        result = RiskClassifier().classify(_make_output(frameworks=frameworks))
        assert result.risk_level in ("MINIMAL", "UNDETERMINED")


class TestRiskClassifierLimited:
    """Moderate signals → LIMITED risk."""

    def test_moderate_framework_with_weak_domain(self):
        frameworks = [
            DetectedFramework(name="scikit-learn", confidence=0.95, hr_relevance_score=0.7),
        ]
        domains = [
            DetectedDomain(
                domain="education",
                annex_iii_category="3",
                confidence=0.5,
                matched_keywords=["student"],
            ),
        ]
        result = RiskClassifier().classify(_make_output(frameworks, domains))
        assert result.risk_level == "LIMITED"
        assert 35 <= result.risk_score < 65


class TestRiskClassifierMultipleDomains:
    """Multiple domains → picks highest-risk category."""

    def test_picks_highest_confidence_domain(self):
        frameworks = [
            DetectedFramework(name="scikit-learn", confidence=0.95, hr_relevance_score=0.8),
        ]
        domains = [
            DetectedDomain(
                domain="education",
                annex_iii_category="3",
                confidence=0.5,
                matched_keywords=["student"],
            ),
            DetectedDomain(
                domain="employment",
                annex_iii_category="4a",
                confidence=0.9,
                matched_keywords=["hiring", "candidate"],
            ),
        ]
        result = RiskClassifier().classify(_make_output(frameworks, domains))
        assert result.annex_iii_category == "4a"


class TestRiskClassifierThresholds:
    """Score boundary tests at exact thresholds."""

    def test_score_at_high_threshold(self):
        """A score of exactly 65 should be HIGH."""
        classifier = RiskClassifier()
        level = classifier._score_to_level(0.65)
        assert level == "HIGH"

    def test_score_just_below_high(self):
        level = RiskClassifier()._score_to_level(0.64)
        assert level == "LIMITED"

    def test_score_at_limited_threshold(self):
        level = RiskClassifier()._score_to_level(0.35)
        assert level == "LIMITED"

    def test_score_just_below_limited(self):
        level = RiskClassifier()._score_to_level(0.34)
        assert level == "MINIMAL"

    def test_score_zero(self):
        level = RiskClassifier()._score_to_level(0.0)
        assert level == "UNDETERMINED"


class TestRiskClassifierEvidence:
    """Evidence chain populated correctly."""

    def test_evidence_has_signal_types(self):
        frameworks = [
            DetectedFramework(name="scikit-learn", confidence=0.95, hr_relevance_score=0.8),
        ]
        domains = [
            DetectedDomain(
                domain="employment",
                annex_iii_category="4a",
                confidence=0.9,
                matched_keywords=["hiring"],
            ),
        ]
        result = RiskClassifier().classify(_make_output(frameworks, domains))
        signal_types = {e["signal_type"] for e in result.evidence}
        assert "framework" in signal_types
        assert "domain" in signal_types

    def test_evidence_includes_weights(self):
        frameworks = [
            DetectedFramework(name="torch", confidence=0.9, hr_relevance_score=0.6),
        ]
        result = RiskClassifier().classify(_make_output(frameworks=frameworks))
        for e in result.evidence:
            assert "weight" in e
            assert e["weight"] > 0

    def test_result_is_risk_classification(self):
        result = RiskClassifier().classify(_make_output())
        assert isinstance(result, RiskClassification)
