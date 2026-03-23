"""Tests for PDF section builders."""

from __future__ import annotations

import pytest
from reportlab.platypus import Flowable, Paragraph, Spacer, Table

from app.schemas.compliance import (
    AssessmentResult,
    CheckEvidence,
    ComplianceCheck,
    ComplianceSummary,
)
from app.schemas.scanner import (
    ConfigSignal,
    DetectedDomain,
    DetectedFramework,
    DocValidation,
    RiskClassification,
    ScannerOutput,
)
from app.services.pdf.sections import (
    build_article_section,
    build_config_signals_section,
    build_doc_validations_section,
    build_domains_section,
    build_footer,
    build_header,
    build_risk_section,
    build_summary_section,
)


class TestBuildHeader:

    def test_returns_flowables(self):
        result = build_header(
            repo_url="https://github.com/org/repo",
            generated_at="2026-03-17 12:00 UTC",
            assessment_id="abcdef12-3456-7890-abcd-ef1234567890",
        )
        assert len(result) > 0
        assert all(isinstance(f, Flowable) for f in result)

    def test_includes_repo_url(self):
        result = build_header(
            repo_url="https://github.com/org/repo",
            generated_at="2026-03-17",
            assessment_id="abc123",
        )
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "github.com/org/repo" in text

    def test_includes_assessment_id_prefix(self):
        result = build_header(
            repo_url="https://github.com/org/repo",
            generated_at="2026-03-17",
            assessment_id="abcdef12-long-id",
        )
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "abcdef12" in text


class TestBuildSummarySection:

    @pytest.fixture
    def summary(self) -> ComplianceSummary:
        return ComplianceSummary(
            total_checks=7,
            passed=3,
            failed=2,
            partial=2,
            compliance_score=55,
            overall_status="PARTIALLY_COMPLIANT",
            critical_failures=["Risk Management System"],
        )

    @pytest.fixture
    def frameworks(self) -> list[DetectedFramework]:
        return [
            DetectedFramework(name="scikit-learn", confidence=0.95, hr_relevance_score=0.7),
            DetectedFramework(name="torch", confidence=0.95, hr_relevance_score=0.5),
        ]

    def test_returns_flowables(self, summary, frameworks):
        result = build_summary_section(summary, frameworks)
        assert len(result) > 0
        assert all(isinstance(f, Flowable) for f in result)

    def test_includes_score(self, summary, frameworks):
        result = build_summary_section(summary, frameworks)
        tables = [f for f in result if isinstance(f, Table)]
        assert len(tables) >= 1

    def test_includes_framework_names(self, summary, frameworks):
        result = build_summary_section(summary, frameworks)
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "scikit-learn" in text
        assert "torch" in text

    def test_empty_frameworks(self, summary):
        result = build_summary_section(summary, [])
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "None" in text

    def test_critical_failures_shown(self, summary, frameworks):
        result = build_summary_section(summary, frameworks)
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "Risk Management System" in text


class TestBuildArticleSection:

    @pytest.fixture
    def failing_check(self) -> ComplianceCheck:
        return ComplianceCheck(
            rule_id="EU_AI_ART_9",
            rule_name="Risk Management System",
            article="Article 9",
            status="FAIL",
            severity="critical",
            evidence=CheckEvidence(
                description="Risk management gaps: no risk assessment found.",
                source="scan://example.com",
            ),
            details={
                "risk_assessment_exists": False,
                "failure_modes_cataloged": False,
                "mitigation_documented": False,
            },
            remediation="Create a risk assessment documenting known risks.",
        )

    @pytest.fixture
    def passing_check(self) -> ComplianceCheck:
        return ComplianceCheck(
            rule_id="EU_AI_ART_11",
            rule_name="Technical Documentation",
            article="Article 11",
            status="PASS",
            severity="critical",
            evidence=CheckEvidence(
                description="Technical documentation complete.",
                source="scan://example.com",
            ),
            details={
                "model_card_exists": True,
                "architecture_documented": True,
                "performance_recorded": True,
            },
        )

    def test_fail_has_remediation(self, failing_check):
        result = build_article_section(failing_check)
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "Remediation" in text
        assert "risk assessment" in text

    def test_pass_no_remediation(self, passing_check):
        result = build_article_section(passing_check)
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "Remediation" not in text

    def test_includes_sub_checks_table(self, failing_check):
        result = build_article_section(failing_check)
        tables = [f for f in result if isinstance(f, Table)]
        # At least status table + sub-checks table
        assert len(tables) >= 2

    def test_returns_flowables(self, passing_check):
        result = build_article_section(passing_check)
        assert all(isinstance(f, Flowable) for f in result)


class TestBuildRiskSection:

    def test_none_returns_empty(self):
        assert build_risk_section(None) == []

    def test_with_data_returns_flowables(self):
        risk = RiskClassification(
            risk_level="HIGH", risk_score=78, confidence=0.88,
            annex_iii_category="4a", evidence=[],
        )
        result = build_risk_section(risk)
        assert len(result) > 0
        assert all(isinstance(f, Flowable) for f in result)

    def test_shows_category(self):
        risk = RiskClassification(
            risk_level="HIGH", risk_score=78, confidence=0.88,
            annex_iii_category="4a", evidence=[],
        )
        result = build_risk_section(risk)
        tables = [f for f in result if isinstance(f, Table)]
        assert len(tables) >= 1


class TestBuildDomainsSection:

    def test_empty_returns_empty(self):
        assert build_domains_section([]) == []

    def test_with_data_returns_flowables(self):
        domains = [
            DetectedDomain(
                domain="employment", annex_iii_category="4a",
                confidence=0.9, matched_keywords=["hiring", "candidate"],
            ),
        ]
        result = build_domains_section(domains)
        assert len(result) > 0
        assert all(isinstance(f, Flowable) for f in result)

    def test_shows_category_and_confidence(self):
        domains = [
            DetectedDomain(
                domain="employment", annex_iii_category="4a",
                confidence=0.85, matched_keywords=["hiring"],
            ),
        ]
        result = build_domains_section(domains)
        tables = [f for f in result if isinstance(f, Table)]
        assert len(tables) >= 1


class TestBuildConfigSignalsSection:

    def test_empty_returns_empty(self):
        assert build_config_signals_section([]) == []

    def test_with_data_returns_flowables(self):
        signals = [
            ConfigSignal(
                source="docker", framework_hint="tensorflow",
                detail="GPU runtime detected", confidence=0.8,
            ),
        ]
        result = build_config_signals_section(signals)
        assert len(result) > 0
        assert all(isinstance(f, Flowable) for f in result)


class TestBuildDocValidationsSection:

    def test_empty_returns_empty(self):
        assert build_doc_validations_section([]) == []

    def test_with_data_returns_flowables(self):
        validations = [
            DocValidation(
                doc_type="model_card",
                sections_found=["description", "metrics"],
                sections_missing=["limitations"],
                completeness_score=0.67,
            ),
        ]
        result = build_doc_validations_section(validations)
        assert len(result) > 0
        assert all(isinstance(f, Flowable) for f in result)

    def test_completeness_score_coloring(self):
        validations = [
            DocValidation(
                doc_type="risk_assessment",
                sections_found=["overview"],
                sections_missing=["mitigations", "testing", "monitoring"],
                completeness_score=0.25,
            ),
        ]
        result = build_doc_validations_section(validations)
        tables = [f for f in result if isinstance(f, Table)]
        assert len(tables) >= 1


class TestBuildFooter:

    def test_returns_flowables(self):
        result = build_footer()
        assert len(result) > 0
        assert all(isinstance(f, Flowable) for f in result)

    def test_includes_methodology(self):
        result = build_footer()
        paragraphs = [f for f in result if isinstance(f, Paragraph)]
        text = " ".join(p.text for p in paragraphs)
        assert "Methodology" in text
