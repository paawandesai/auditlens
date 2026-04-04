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
from app.schemas.scanner import (
    ConfigSignal,
    DetectedDomain,
    DetectedFramework,
    DocValidation,
    RiskClassification,
)
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
    *,
    is_adversarial: bool = False,
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

    # Assessment type / frameworks
    if is_adversarial:
        flowables.append(
            Paragraph("<b>Assessment Type:</b> Adversarial Security Testing", BODY_STYLE)
        )
    elif frameworks:
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


def build_advisory_header(risk_tier: str) -> list[Flowable]:
    """Header for the advisory (informational) section of the report."""
    return [
        Spacer(1, 16),
        Paragraph("Advisory Checks (Informational)", HEADING_STYLE),
        Paragraph(
            f"This <b>{risk_tier}</b>-risk system is assessed against Articles 5 and 50. "
            "Articles 9\u201315 below are shown for informational purposes only "
            "and do not affect the compliance score.",
            SMALL_STYLE,
        ),
        Spacer(1, 8),
    ]


def build_article_section(
    check: ComplianceCheck, *, advisory: bool = False,
) -> list[Flowable]:
    """Single article compliance check section with status, evidence, and remediation."""
    flowables: list[Flowable] = []

    # Section heading with status badge
    status_color = STATUS_COLORS.get(check.status, colors.gray)
    severity_color = SEVERITY_COLORS.get(check.severity, colors.gray)

    # Advisory sections use muted grey heading
    heading_style = SMALL_STYLE if advisory else HEADING_STYLE
    prefix = "[Advisory] " if advisory else ""

    flowables.append(
        Paragraph(
            f"{prefix}{check.article}: {check.rule_name}",
            heading_style,
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

    # Rich sub-checks (with reasoning, article reference) — preferred
    rich_subs = check.sub_checks if hasattr(check, "sub_checks") else []
    if rich_subs:
        sub_data = [["Sub-check", "Result", "Detail"]]
        for sc in rich_subs:
            result_text = "PASS" if sc.passed else "FAIL"
            detail = sc.reasoning[:120]
            if sc.article_reference:
                detail += f" {sc.article_reference[:60]}"
            sub_data.append([sc.description[:50], result_text, detail])

        sub_table = Table(sub_data, colWidths=[2.0 * inch, 0.8 * inch, 3.0 * inch])
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for row_idx, sc in enumerate(rich_subs, start=1):
            cell_color = STATUS_COLORS["PASS"] if sc.passed else STATUS_COLORS["FAIL"]
            style_cmds.append(("BACKGROUND", (1, row_idx), (1, row_idx), cell_color))
            style_cmds.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), colors.white))
            style_cmds.append(("ALIGN", (1, row_idx), (1, row_idx), "CENTER"))

        sub_table.setStyle(TableStyle(style_cmds))
        flowables.append(Spacer(1, 4))
        flowables.append(sub_table)
    else:
        # Fallback: old boolean sub-checks from details dict
        bool_subs = {
            k: v for k, v in (check.details or {}).items()
            if isinstance(v, bool)
        }
        if bool_subs:
            sub_data = [["Sub-check", "Result"]]
            for name, passed in bool_subs.items():
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
            for row_idx, (_, passed) in enumerate(bool_subs.items(), start=1):
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


def build_risk_section(risk: RiskClassification | None) -> list[Flowable]:
    """Risk classification summary — level, score, category."""
    if risk is None:
        return []

    flowables: list[Flowable] = []
    flowables.append(Paragraph("Risk Classification", HEADING_STYLE))

    level_colors = {
        "HIGH": colors.HexColor("#d93636"),
        "UNACCEPTABLE": colors.HexColor("#8b0000"),
        "LIMITED": colors.HexColor("#f2a60d"),
        "MINIMAL": colors.HexColor("#2eb872"),
        "UNDETERMINED": colors.HexColor("#888888"),
    }
    level_color = level_colors.get(risk.risk_level, colors.gray)

    data = [
        ["Risk Level", risk.risk_level],
        ["Risk Score", f"{risk.risk_score}/100"],
        ["Confidence", f"{risk.confidence:.0%}"],
    ]
    if risk.annex_iii_category:
        data.append(["Annex III Category", risk.annex_iii_category])

    table = Table(data, colWidths=[2.0 * inch, 3.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("BACKGROUND", (1, 0), (1, 0), level_color),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    flowables.append(table)
    flowables.append(Spacer(1, 12))
    return flowables


def build_domains_section(domains: list[DetectedDomain]) -> list[Flowable]:
    """Annex III domain classification table."""
    if not domains:
        return []

    flowables: list[Flowable] = []
    flowables.append(Paragraph("Annex III Domain Classification", HEADING_STYLE))

    data = [["Domain", "Category", "Confidence", "Keywords"]]
    for d in domains:
        keywords = ", ".join(d.matched_keywords[:4])
        data.append([
            d.domain.replace("_", " ").title(),
            d.annex_iii_category,
            f"{d.confidence:.0%}",
            keywords,
        ])

    table = Table(data, colWidths=[1.5 * inch, 1.0 * inch, 1.0 * inch, 2.0 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a3f8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    flowables.append(table)
    flowables.append(Spacer(1, 10))
    return flowables


def build_config_signals_section(signals: list[ConfigSignal]) -> list[Flowable]:
    """Infrastructure AI signals table."""
    if not signals:
        return []

    flowables: list[Flowable] = []
    flowables.append(Paragraph("Infrastructure AI Signals", HEADING_STYLE))

    data = [["Source", "Framework", "Detail"]]
    for s in signals:
        data.append([s.source.upper(), s.framework_hint, s.detail])

    table = Table(data, colWidths=[1.0 * inch, 1.5 * inch, 3.0 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b45309")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    flowables.append(table)
    flowables.append(Spacer(1, 10))
    return flowables


def build_doc_validations_section(validations: list[DocValidation]) -> list[Flowable]:
    """Document completeness assessment table."""
    if not validations:
        return []

    flowables: list[Flowable] = []
    flowables.append(Paragraph("Document Completeness", HEADING_STYLE))

    data = [["Document", "Completeness", "Found", "Missing"]]
    for v in validations:
        found = ", ".join(v.sections_found[:3]) or "—"
        missing = ", ".join(v.sections_missing[:3]) or "—"
        pct = f"{v.completeness_score:.0%}"
        data.append([v.doc_type.replace("_", " ").title(), pct, found, missing])

    table = Table(data, colWidths=[1.5 * inch, 1.0 * inch, 1.5 * inch, 1.5 * inch])

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    # Color-code completeness cells
    for row_idx, v in enumerate(validations, start=1):
        if v.completeness_score >= 0.8:
            cell_color = colors.HexColor("#2eb872")
        elif v.completeness_score >= 0.5:
            cell_color = colors.HexColor("#f2a60d")
        else:
            cell_color = colors.HexColor("#d93636")
        style_cmds.append(("BACKGROUND", (1, row_idx), (1, row_idx), cell_color))
        style_cmds.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), colors.white))

    table.setStyle(TableStyle(style_cmds))
    flowables.append(table)
    flowables.append(Spacer(1, 10))
    return flowables


def build_adversarial_summary_section(findings: list[dict]) -> list[Flowable]:
    """Adversarial testing results — category breakdown and critical findings.

    Returns empty list if no findings. Only appears when red team data is present.
    """
    if not findings:
        return []

    flowables: list[Flowable] = []
    flowables.append(Paragraph("Adversarial Testing Results", HEADING_STYLE))

    # Compute totals
    total = len(findings)
    passed = sum(1 for f in findings if f.get("grade") == "pass")
    failed = sum(1 for f in findings if f.get("grade") in ("fail", "critical_fail"))
    critical = sum(1 for f in findings if f.get("grade") == "critical_fail")

    flowables.append(
        Paragraph(
            f"<b>{total}</b> tests &nbsp;|&nbsp; "
            f"<font color='#2eb872'><b>{passed}</b> passed</font> &nbsp;|&nbsp; "
            f"<font color='#d93636'><b>{failed}</b> failed</font> &nbsp;|&nbsp; "
            f"<font color='#8b0000'><b>{critical}</b> critical</font>",
            BODY_STYLE,
        )
    )
    flowables.append(Spacer(1, 8))

    # Category breakdown table
    categories: dict[str, dict[str, int]] = {}
    for f in findings:
        cat = f.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "pass": 0, "fail": 0}
        categories[cat]["total"] += 1
        if f.get("grade") == "pass":
            categories[cat]["pass"] += 1
        elif f.get("grade") in ("fail", "critical_fail", "partial_fail"):
            categories[cat]["fail"] += 1

    cat_data = [["Category", "Tests", "Pass", "Fail", "Pass Rate"]]
    cat_rates: list[float] = []
    for cat_name, counts in sorted(categories.items()):
        rate = counts["pass"] / counts["total"] if counts["total"] > 0 else 0.0
        cat_rates.append(rate)
        cat_data.append([
            cat_name.replace("-", " ").replace("_", " ").title(),
            str(counts["total"]),
            str(counts["pass"]),
            str(counts["fail"]),
            f"{rate:.0%}",
        ])

    cat_table = Table(cat_data, colWidths=[2.0 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 1.0 * inch])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a3f8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    # Color-code pass rate cells
    for row_idx, rate in enumerate(cat_rates, start=1):
        if rate >= 0.8:
            cell_color = colors.HexColor("#2eb872")
        elif rate >= 0.5:
            cell_color = colors.HexColor("#f2a60d")
        else:
            cell_color = colors.HexColor("#d93636")
        style_cmds.append(("BACKGROUND", (4, row_idx), (4, row_idx), cell_color))
        style_cmds.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), colors.white))

    cat_table.setStyle(TableStyle(style_cmds))
    flowables.append(cat_table)
    flowables.append(Spacer(1, 10))

    # Critical findings detail (severity >= 4 AND grade in fail/critical_fail)
    critical_findings = [
        f for f in findings
        if f.get("severity", 0) >= 4 and f.get("grade") in ("fail", "critical_fail")
    ][:10]  # Cap at 10

    if critical_findings:
        flowables.append(Paragraph("Critical Findings Detail", SUBTITLE_STYLE))
        flowables.append(Spacer(1, 4))

        for cf in critical_findings:
            severity_badge = f"SEV-{cf.get('severity', '?')}"
            grade_text = cf.get("grade", "").replace("_", " ").upper()
            category = cf.get("category", "unknown").replace("-", " ").replace("_", " ").title()
            article = cf.get("mapped_article", "")
            reasoning = cf.get("reasoning", "No details provided.")

            flowables.append(
                Paragraph(
                    f"<b>{category}</b> &nbsp; "
                    f"<font color='#d93636'>[{severity_badge}]</font> &nbsp; "
                    f"<font color='#d93636'>{grade_text}</font>"
                    f"{f' &nbsp; → {article}' if article else ''}",
                    BODY_STYLE,
                )
            )
            flowables.append(
                Paragraph(reasoning[:300], REMEDIATION_STYLE)
            )
            flowables.append(Spacer(1, 4))

    flowables.append(Spacer(1, 10))
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
