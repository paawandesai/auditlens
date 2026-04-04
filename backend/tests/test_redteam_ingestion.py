"""Tests for red team ingestion — mapper logic and API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.redteam import RedTeamFinding, RedTeamScanResult
from app.services.redteam_mapper import map_redteam_to_assessment


@pytest.fixture
def api_client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

def _make_finding(**overrides) -> dict:
    base = {
        "finding_id": "f-001",
        "category": "prompt-injection-rag",
        "severity": 4,
        "grade": "fail",
        "confidence": 0.95,
        "reasoning": "Model followed injected instructions in retrieved context.",
    }
    return {**base, **overrides}


MIXED_SCAN = {
    "scan_id": "rt-mixed-001",
    "timestamp": "2026-04-02T10:00:00Z",
    "target": {"name": "test-agent", "version": "1.0"},
    "findings": [
        _make_finding(finding_id="f-001", category="prompt-injection-rag", grade="fail"),
        _make_finding(finding_id="f-002", category="prompt-injection-rag", grade="pass"),
        _make_finding(finding_id="f-003", category="tool-misuse", grade="critical_fail"),
        _make_finding(finding_id="f-004", category="cross-agent-injection", grade="partial_fail"),
        _make_finding(finding_id="f-005", category="memory-poisoning", grade="pass"),
    ],
}

ALL_PASS_SCAN = {
    "scan_id": "rt-pass-001",
    "findings": [
        _make_finding(finding_id="f-010", category="prompt-injection-rag", grade="pass"),
        _make_finding(finding_id="f-011", category="tool-misuse", grade="pass"),
    ],
}


# ---------------------------------------------------------------------------
# Mapper unit tests
# ---------------------------------------------------------------------------

class TestRedteamMapper:

    def test_findings_map_to_correct_articles(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)

        articles = {c.article for c in assessment.checks}
        # prompt-injection-rag → Art 9, tool-misuse → Art 14,
        # cross-agent-injection → Art 15, memory-poisoning → Art 12
        assert articles == {"Article 9", "Article 12", "Article 14", "Article 15"}

    def test_mixed_findings_produce_correct_statuses(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)

        by_article = {c.article: c.status for c in assessment.checks}
        # Art 9: has fail + pass → FAIL
        assert by_article["Article 9"] == "FAIL"
        # Art 14: has critical_fail → FAIL
        assert by_article["Article 14"] == "FAIL"
        # Art 15: has partial_fail → PARTIAL
        assert by_article["Article 15"] == "PARTIAL"
        # Art 12: all pass → PASS
        assert by_article["Article 12"] == "PASS"

    def test_all_pass_produces_compliant(self):
        scan = RedTeamScanResult(**ALL_PASS_SCAN)
        assessment = map_redteam_to_assessment(scan)

        assert assessment.summary.overall_status == "COMPLIANT"
        assert assessment.summary.compliance_score == 100

    def test_mixed_produces_non_compliant(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)

        assert assessment.summary.overall_status == "NON_COMPLIANT"
        assert assessment.summary.compliance_score < 100

    def test_subchecks_match_finding_count(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)

        total_subchecks = sum(len(c.sub_checks) for c in assessment.checks)
        assert total_subchecks == len(MIXED_SCAN["findings"])

    def test_evidence_source_is_adversarial_test(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)

        for check in assessment.checks:
            assert check.evidence_source == "adversarial_test"
            assert check.evidence.source == "red_team_scan"
            assert check.details["evidence_source"] == "adversarial_testing"

    def test_severity_matches_article_meta(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)

        by_article = {c.article: c.severity for c in assessment.checks}
        assert by_article["Article 9"] == "critical"
        assert by_article["Article 12"] == "high"
        assert by_article["Article 14"] == "critical"
        assert by_article["Article 15"] == "critical"

    def test_remediation_present_on_failed_checks(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)

        for check in assessment.checks:
            if check.status != "PASS":
                assert check.remediation is not None
                assert len(check.remediation) > 0

    def test_unknown_category_defaults_to_article_9(self):
        scan = RedTeamScanResult(
            scan_id="rt-unknown",
            findings=[_make_finding(category="novel-attack-vector", grade="fail")],
        )
        assessment = map_redteam_to_assessment(scan)
        assert assessment.checks[0].article == "Article 9"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestIngestEndpoint:

    def test_returns_assessment(self, api_client):
        resp = api_client.post("/api/v1/redteam/ingest", json=MIXED_SCAN)
        assert resp.status_code == 200
        data = resp.json()
        assert data["scan_id"] == "rt-mixed-001"
        assert "assessment" in data
        assert len(data["assessment"]["checks"]) == 4

    def test_all_pass_scan(self, api_client):
        resp = api_client.post("/api/v1/redteam/ingest", json=ALL_PASS_SCAN)
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment"]["summary"]["overall_status"] == "COMPLIANT"


class TestIngestPdfEndpoint:

    def test_returns_pdf_bytes(self, api_client):
        resp = api_client.post("/api/v1/redteam/ingest/pdf", json=MIXED_SCAN)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF magic bytes
        assert resp.content[:4] == b"%PDF"

    def test_pdf_filename_contains_scan_id(self, api_client):
        resp = api_client.post("/api/v1/redteam/ingest/pdf", json=MIXED_SCAN)
        assert "rt-mixed-001" in resp.headers["content-disposition"]


# ---------------------------------------------------------------------------
# evidence_source field tests
# ---------------------------------------------------------------------------

class TestEvidenceSourceField:

    def test_default_is_repo_scan(self):
        """Existing ComplianceChecks default to repo_scan."""
        from app.schemas.compliance import CheckEvidence, ComplianceCheck

        check = ComplianceCheck(
            rule_id="TEST",
            rule_name="Test",
            article="Article 9",
            status="PASS",
            severity="medium",
            evidence=CheckEvidence(description="test", source="test"),
            details={},
        )
        assert check.evidence_source == "repo_scan"

    def test_redteam_checks_are_adversarial_test(self):
        scan = RedTeamScanResult(**MIXED_SCAN)
        assessment = map_redteam_to_assessment(scan)
        for check in assessment.checks:
            assert check.evidence_source == "adversarial_test"


# ---------------------------------------------------------------------------
# Adversarial PDF section tests
# ---------------------------------------------------------------------------

class TestAdversarialPdfSection:

    def test_section_builds_with_findings(self):
        from app.services.pdf.sections import build_adversarial_summary_section

        findings = [
            {"category": "prompt-injection-rag", "grade": "fail", "severity": 4, "reasoning": "Injected", "mapped_article": "Article 9"},
            {"category": "prompt-injection-rag", "grade": "pass", "severity": 2, "reasoning": "Blocked"},
            {"category": "tool-misuse", "grade": "critical_fail", "severity": 5, "reasoning": "Unrestricted tool call"},
        ]
        flowables = build_adversarial_summary_section(findings)
        assert len(flowables) > 0

    def test_section_empty_for_no_findings(self):
        from app.services.pdf.sections import build_adversarial_summary_section

        assert build_adversarial_summary_section([]) == []

    def test_repo_scan_pdf_has_no_adversarial_section(self, api_client):
        """Existing repo scan PDFs should not include the adversarial section."""
        from app.schemas.scanner import ScannerOutput
        from app.services.compliance.base import ComplianceEngine
        from app.services.compliance.article_09 import Article09Check
        from app.services.pdf.report_builder import generate_compliance_pdf

        scanner_output = ScannerOutput(repo_url="https://github.com/test/repo")
        engine = ComplianceEngine([Article09Check()])
        assessment = engine.run(scanner_output)

        # Verify no checks have adversarial evidence_source
        for check in assessment.checks:
            assert check.evidence_source == "repo_scan"

        pdf = generate_compliance_pdf(assessment, scanner_output)
        assert pdf[:5] == b"%PDF-"
