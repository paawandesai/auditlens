"""Tests for PDF report builder — integration tests producing real PDFs."""

from __future__ import annotations

import pytest

from app.schemas.scanner import ScannerOutput
from app.services.compliance.article_09 import Article09Check
from app.services.compliance.article_10 import Article10Check
from app.services.compliance.article_11 import Article11Check
from app.services.compliance.article_12 import Article12Check
from app.services.compliance.article_13 import Article13Check
from app.services.compliance.article_14 import Article14Check
from app.services.compliance.article_15 import Article15Check
from app.services.compliance.base import ComplianceEngine
from app.services.pdf.report_builder import generate_compliance_pdf

ALL_CHECKS = [
    Article09Check(),
    Article10Check(),
    Article11Check(),
    Article12Check(),
    Article13Check(),
    Article14Check(),
    Article15Check(),
]


def _generate(scanner_output: ScannerOutput) -> bytes:
    engine = ComplianceEngine(ALL_CHECKS)
    assessment = engine.run(scanner_output)
    return generate_compliance_pdf(assessment, scanner_output)


class TestGeneratePdf:

    def test_returns_valid_pdf_bytes(self, fully_compliant_scanner_output):
        pdf = _generate(fully_compliant_scanner_output)
        assert isinstance(pdf, bytes)
        assert pdf[:5] == b"%PDF-"

    def test_non_empty_output(self, fully_compliant_scanner_output):
        pdf = _generate(fully_compliant_scanner_output)
        assert len(pdf) > 1000  # A real PDF should be at least a few KB

    def test_compliant_report(self, fully_compliant_scanner_output):
        pdf = _generate(fully_compliant_scanner_output)
        assert pdf[:5] == b"%PDF-"

    def test_non_compliant_report(self, non_compliant_scanner_output):
        pdf = _generate(non_compliant_scanner_output)
        assert pdf[:5] == b"%PDF-"

    def test_partial_report(self, partial_scanner_output):
        pdf = _generate(partial_scanner_output)
        assert pdf[:5] == b"%PDF-"

    def test_minimal_report(self, minimal_scanner_output):
        pdf = _generate(minimal_scanner_output)
        assert pdf[:5] == b"%PDF-"

    def test_no_frameworks(self, minimal_scanner_output):
        pdf = _generate(minimal_scanner_output)
        assert len(pdf) > 500
