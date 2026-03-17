"""PDF section builders — pure functions returning lists of Flowables.

Each function takes data and returns reportlab Flowable objects.
No I/O, no side effects. Composable by report_builder.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.compliance import AssessmentResult, ComplianceCheck, ComplianceSummary
from app.schemas.scanner import DetectedFramework
from app.services.pdf.styles import (
    BODY_STYLE,
    HEADING_STYLE,
    OVERALL_STATUS_COLORS,
    REMEDIATION_STYLE,
    SEVERITY_COLORS,
    SMALL_STYLE,
    STATUS_COLORS,
    SUBTITLE_STYLE,
    TITLE_STYLE,
)


def build_header(
    repo_url: str,
    generated_at: str,
    assessment_id: str,
) -> list[Flowable]:
    """Title block with repo URL, date, and assessment ID."""
    return [
        Paragraph("AuditLens Compliance Report", TITLE_STYLE),
        Paragraph(f"Repository: {repo_url}", SUBTITLE_STYLE),
        Paragraph(
            f"Generated: {generated_at} &nbsp;&nbsp;|&nbsp;&nbsp; ID: {assessment_id[:8]}",
            SMALL_STYLE,
        ),
        Spacer(1, 12),
    ]


def build_summary_section(
    summary: ComplianceSummary,
    frameworks: list[DetectedFramework],
) -> list[Flowable]:
    """Overall status banner, score, pass/fail counts, framework list."""
    flowables: list[Flowable] = []

    # Overall status banner
    status_color = OVERALL_STATUS_COLORS.get(summary.overall_status, colors.gray)
    status_label = summary.overall_status.replace("_", " ")
    flowables.append(Paragraph("Executive Summary", HEADING_STYLE))

    # Summary table: status, score, counts
    summary_data = [
        ["Overall Status", status_label],
        ["Compliance Score", f"{summary.compliance_score}/100"],
        ["Checks Passed", str(summary.passed)],
        ["Checks Failed", str(summary.failed)],
        ["Checks Partial", str(summary.partial)],
    ]

    summary_table = Table(summary_data, colWidths=[2.0 * inch, 3.5 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("BACKGROUND", (1, 0), (1, 0), status_color),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    flowables.append(summary_table)
    flowables.append(Spacer(1, 8))

    # Frameworks detected
    if frameworks:
        fw_names = ", ".join(f.name for f in frameworks)
        flowables.append(
            Paragraph(f"<b>AI/ML Frameworks Detected:</b> {fw_names}", BODY_STYLE)
        )
    else:
        flowables.append(
            Paragraph("<b>AI/ML Frameworks Detected:</b> None", BODY_STYLE)
        )

    # Critical failures callout
    if summary.critical_failures:
        crit_text = ", ".join(summary.critical_failures)
        flowables.append(
            Paragraph(
                f"<b>Critical Failures:</b> <font color='#d93636'>{crit_text}</font>",
                BODY_STYLE,
            )
        )

    flowables.append(Spacer(1, 12))
    return flowables


def build_article_section(check: ComplianceCheck) -> list[Flowable]:
    """Single article compliance check section with status, evidence, and remediation."""
    flowables: list[Flowable] = []

    # Section heading with status badge
    status_color = STATUS_COLORS.get(check.status, colors.gray)
    severity_color = SEVERITY_COLORS.get(check.severity, colors.gray)

    flowables.append(
        Paragraph(
            f"{check.article}: {check.rule_name}",
            HEADING_STYLE,
        )
    )

    # Status + severity row
    status_data = [
        ["Status", check.status, "Severity", check.severity.upper()],
    ]
    status_table = Table(status_data, colWidths=[1.0 * inch, 1.5 * inch, 1.0 * inch, 1.5 * inch])
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 0), status_color),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
        ("BACKGROUND", (3, 0), (3, 0), severity_color),
        ("TEXTCOLOR", (3, 0), (3, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    flowables.append(status_table)
    flowables.append(Spacer(1, 4))

    # Evidence description
    flowables.append(
        Paragraph(f"<b>Evidence:</b> {check.evidence.description}", BODY_STYLE)
    )

    # Sub-checks table
    sub_checks = {
        k: v for k, v in (check.details or {}).items()
        if isinstance(v, bool)
    }
    if sub_checks:
        sub_data = [["Sub-check", "Result"]]
        for name, passed in sub_checks.items():
            label = name.replace("_", " ").title()
            result_text = "PASS" if passed else "FAIL"
            sub_data.append([label, result_text])

        sub_table = Table(sub_data, colWidths=[3.5 * inch, 1.5 * inch])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]
        # Color-code pass/fail cells
        for row_idx, (_, passed) in enumerate(sub_checks.items(), start=1):
            cell_color = STATUS_COLORS["PASS"] if passed else STATUS_COLORS["FAIL"]
            style_cmds.append(("BACKGROUND", (1, row_idx), (1, row_idx), cell_color))
            style_cmds.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), colors.white))
            style_cmds.append(("ALIGN", (1, row_idx), (1, row_idx), "CENTER"))

        sub_table.setStyle(TableStyle(style_cmds))
        flowables.append(Spacer(1, 4))
        flowables.append(sub_table)

    # Remediation
    if check.remediation:
        flowables.append(Spacer(1, 4))
        flowables.append(
            Paragraph(f"<b>Remediation:</b> {check.remediation}", REMEDIATION_STYLE)
        )

    flowables.append(Spacer(1, 8))
    return flowables


def build_footer() -> list[Flowable]:
    """Methodology disclaimer and branding."""
    return [
        Spacer(1, 20),
        Paragraph(
            "<b>Methodology:</b> This report was generated by AuditLens automated scanning. "
            "Compliance signals are detected through file-presence analysis, dependency parsing, "
            "and keyword matching against repository contents. This assessment is indicative "
            "and should be supplemented with manual review for formal compliance certification.",
            SMALL_STYLE,
        ),
        Spacer(1, 8),
        Paragraph(
            "AuditLens &mdash; EU AI Act Compliance Evidence &mdash; auditlens.ai",
            SMALL_STYLE,
        ),
    ]
