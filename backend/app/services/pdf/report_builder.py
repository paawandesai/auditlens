"""PDF report orchestrator — single public function.

Composes section builders into a complete audit-ready PDF.
Pure function: assessment in, PDF bytes out. No file I/O.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate

from app.schemas.compliance import AssessmentResult
from app.schemas.scanner import ScannerOutput
from app.services.pdf.sections import (
    build_article_section,
    build_footer,
    build_header,
    build_summary_section,
)

# Sort articles by number for consistent report ordering
_ARTICLE_ORDER = {
    "Article 9": 0,
    "Article 10": 1,
    "Article 11": 2,
    "Article 12": 3,
    "Article 13": 4,
    "Article 14": 5,
    "Article 15": 6,
}


def generate_compliance_pdf(
    assessment: AssessmentResult,
    scanner_output: ScannerOutput,
) -> bytes:
    """Generate a complete audit-ready PDF report.

    Args:
        assessment: Full compliance assessment result.
        scanner_output: Scanner output with detected frameworks.

    Returns:
        PDF file content as bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=40,
        bottomMargin=40,
        leftMargin=50,
        rightMargin=50,
    )

    flowables = []

    # Header
    flowables.extend(
        build_header(
            repo_url=scanner_output.repo_url,
            generated_at=assessment.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            assessment_id=assessment.assessment_id,
        )
    )

    # Executive summary
    flowables.extend(
        build_summary_section(
            summary=assessment.summary,
            frameworks=scanner_output.detected_frameworks,
        )
    )

    # Article sections — sorted by article number
    sorted_checks = sorted(
        assessment.checks,
        key=lambda c: _ARTICLE_ORDER.get(c.article, 99),
    )
    for check in sorted_checks:
        flowables.extend(build_article_section(check))

    # Footer
    flowables.extend(build_footer())

    doc.build(flowables)
    return buffer.getvalue()
