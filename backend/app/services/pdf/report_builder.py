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
    build_adversarial_summary_section,
    build_regulatory_exposure_section,
    build_advisory_header,
    build_article_section,
    build_config_signals_section,
    build_doc_validations_section,
    build_domains_section,
    build_executive_paragraph,
    build_footer,
    build_header,
    build_not_applicable_section,
    build_risk_section,
    build_scope_section,
    build_summary_section,
)

# Sort articles by number for consistent report ordering
_ARTICLE_ORDER = {
    "Article 5": -2,
    "Article 50": -1,
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

    is_adversarial = all(
        c.evidence_source == "adversarial_test" for c in assessment.checks
    ) if assessment.checks else False

    # Header
    flowables.extend(
        build_header(
            repo_url=scanner_output.repo_url,
            generated_at=assessment.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            assessment_id=assessment.assessment_id,
        )
    )

    # Scope statement (only for repo-scan style assessments — adversarial reports
    # have their own scope semantics tied to the red-team target).
    if not is_adversarial:
        flowables.extend(build_scope_section(assessment))

    # Executive summary
    flowables.extend(
        build_summary_section(
            summary=assessment.summary,
            frameworks=scanner_output.detected_frameworks,
            is_adversarial=is_adversarial,
        )
    )

    # Plain-English executive paragraph (only for repo-scan style)
    if not is_adversarial:
        flowables.extend(build_executive_paragraph(assessment))

    # Risk classification
    flowables.extend(build_risk_section(scanner_output.risk_classification))

    # New signal sections
    flowables.extend(build_domains_section(scanner_output.detected_domains))
    flowables.extend(build_config_signals_section(scanner_output.config_signals))
    flowables.extend(build_doc_validations_section(scanner_output.doc_validations))

    # Scored article sections — sorted by article number
    sorted_checks = sorted(
        assessment.checks,
        key=lambda c: _ARTICLE_ORDER.get(c.article, 99),
    )
    for check in sorted_checks:
        flowables.extend(build_article_section(check))

    # Adversarial testing section (only when red team data present)
    adversarial_checks = [
        c for c in assessment.checks if c.evidence_source == "adversarial_test"
    ]
    if adversarial_checks:
        # Severity mapping: critical article checks → severity 4, high → 3
        _sev_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        adversarial_findings = []
        for check in adversarial_checks:
            base_severity = _sev_map.get(check.severity, 2)
            for sc in check.sub_checks:
                adversarial_findings.append({
                    "category": sc.description.split("/")[0],
                    "grade": "pass" if sc.passed else "fail",
                    "severity": base_severity,
                    "reasoning": sc.reasoning,
                    "mapped_article": check.article,
                })
        flowables.extend(build_adversarial_summary_section(adversarial_findings))

    # Advisory sections (Art. 9-15 for non-HIGH risk, informational only)
    if assessment.advisory_checks:
        flowables.extend(
            build_advisory_header(assessment.risk_tier or "UNDETERMINED")
        )
        sorted_advisory = sorted(
            assessment.advisory_checks,
            key=lambda c: _ARTICLE_ORDER.get(c.article, 99),
        )
        for check in sorted_advisory:
            flowables.extend(build_article_section(check, advisory=True))

    # Regulatory exposure (only if any APPLICABLE checks failed)
    flowables.extend(build_regulatory_exposure_section(assessment.checks))

    # Articles Not Applicable — single compact table at the bottom
    flowables.extend(build_not_applicable_section(assessment.checks))

    # Footer
    flowables.extend(build_footer())

    doc.build(flowables)
    return buffer.getvalue()
