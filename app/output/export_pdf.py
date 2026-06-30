from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from typing import TYPE_CHECKING, Any

from app.output.summary_builder import AnamnesisSummary
from app.output.scenario_display import get_scenario_title
from app.patient_import.patient_schema import PatientRecord

SEVERITY_TEXT_COLORS = {
    "critical": "#9f1d20",
    "warning": "#b55a07",
    "info": "#60716d",
}

if TYPE_CHECKING:
    from reportlab.lib.styles import ParagraphStyle


def build_preview_html(
    summary: AnamnesisSummary, patient: PatientRecord
) -> str:
    patient_name = f"{patient.first_name} {patient.last_name}"
    rows = [
        ("Name", patient_name),
        ("Patienten-ID", patient.patient_id),
        ("Geburtsdatum", patient.date_of_birth),
        ("Vorerkrankungen", patient.conditions or "keine"),
        ("Medikamente", ", ".join(patient.medications) if patient.medications else "keine"),
    ]
    html_parts = [
        _html_section("Patientendaten", rows),
    ]

    if summary.red_flags:
        html_parts.append(_html_section_raw("Red Flags", _red_flags_html(summary.red_flags)))

    if summary.grouped_sections:
        for title, fields in summary.grouped_sections.items():
            items = list(fields.items())
            html_parts.append(_html_section(title, items))
    else:
        html_parts.append(_html_section("Anamnese-Antworten", list(summary.answers.items())))

    vitals_rows = _vital_rows(summary)
    html_parts.append(_html_section("Vitalparameter", vitals_rows))

    if summary.open_points:
        items = "".join(f"<li>{p}</li>" for p in summary.open_points)
        html_parts.append(
            _html_section_raw("Offene Punkte", f"<ul>{items}</ul>")
        )

    scenario_text = (
        f"{escape(get_scenario_title(summary.scenario))} &mdash; "
        if summary.scenario
        else ""
    )
    timestamp = summary.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")

    return (
        '<!DOCTYPE html>\n<html lang="de">\n<head><meta charset="utf-8">\n'
        "<style>\n"
        "  body { font-family: 'Segoe UI', Arial, sans-serif; color: #17342f; margin: 30px; }\n"
        "  h1 { color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 6px; }\n"
        "  h2 { color: #17342f; margin-top: 20px; }\n"
        "  table { border-collapse: collapse; table-layout: fixed; width: 100%; margin: 8px 0; }\n"
        "  td, th { padding: 6px 10px; text-align: left; border: 1px solid #ddd; overflow-wrap: anywhere; word-break: break-word; }\n"
        "  th { background: #d6efe9; font-weight: 600; }\n"
        "  .label { color: #60716d; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; }\n"
        "  .value { font-size: 1em; }\n"
        "  .footer { margin-top: 30px; font-size: 0.8em; color: #60716d; border-top: 1px solid #ddd; padding-top: 10px; }\n"
        "</style></head>\n<body>\n"
        f"  <h1>Anamnese-Zusammenfassung</h1>\n"
        f"  <p><em>Szenario: {scenario_text}Erstellt: {timestamp}</em></p>\n"
        f"{''.join(html_parts)}\n"
        '<div class="footer">Dieses Dokument wurde automatisch generiert.</div>\n'
        "</body>\n</html>"
    )


def _html_section(title: str, rows: list[tuple[str, str]]) -> str:
    table_rows = "".join(
        f"<tr><td class='label'>{label}</td><td class='value'>{value}</td></tr>"
        for label, value in rows
    )
    return f"<h2>{title}</h2><table>{table_rows}</table>"


def _html_section_raw(title: str, html: str) -> str:
    return f"<h2>{title}</h2>{html}"


def _red_flags_html(red_flags: list[Any]) -> str:
    rows = [
        '<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">'
        '<tr style="background:#f0f0f0"><th>ID</th><th>Schwere</th><th>Beschreibung</th></tr>'
    ]
    for rf in red_flags:
        severity_color = _severity_text_color(rf.severity)
        severity_label = _severity_label(rf.severity)
        rows.append(
            f"<tr><td>{escape(str(rf.rule_id))}</td>"
            f"<td style='color:{severity_color};font-weight:700'>"
            f"{escape(severity_label)}</td>"
            f"<td>{escape(str(rf.description))}</td></tr>"
        )
    rows.append("</table>")
    return "".join(rows)


def _vital_rows(summary: AnamnesisSummary) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for key, value in summary.vitals.items():
        source = summary.vital_sources.get(key, summary.vitals_source or "nicht dokumentiert")
        rows.append((key, f"{value} (Quelle: {source})"))
    if not rows:
        rows.append(("Status", "nicht erhoben"))
    return rows


def export_summary_pdf(
    summary: AnamnesisSummary, patient: PatientRecord
) -> bytes:
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Das Python-Paket 'reportlab' fehlt. Bitte installiere die "
            "Projektabhaengigkeiten mit 'pip install -r requirements.txt'."
        ) from exc

    accent_color = HexColor("#0f766e")
    danger_color = HexColor("#9f1d20")
    warning_color = HexColor("#b55a07")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        compress=False,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        textColor=accent_color,
        spaceAfter=4 * mm,
    )
    heading_style = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        textColor=HexColor("#17342f"),
        spaceBefore=6 * mm,
        spaceAfter=2 * mm,
    )
    label_style = ParagraphStyle(
        "LabelCustom",
        parent=styles["Normal"],
        textColor=HexColor("#60716d"),
        fontName="Helvetica-Bold",
        fontSize=8,
        spaceAfter=1 * mm,
        splitLongWords=1,
    )
    value_style = ParagraphStyle(
        "ValueCustom",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=2 * mm,
        splitLongWords=1,
    )
    severity_critical_style = ParagraphStyle(
        "SeverityCritical",
        parent=value_style,
        textColor=danger_color,
        fontName="Helvetica-Bold",
    )
    severity_warning_style = ParagraphStyle(
        "SeverityWarning",
        parent=value_style,
        textColor=warning_color,
        fontName="Helvetica-Bold",
    )
    severity_info_style = ParagraphStyle(
        "SeverityInfo",
        parent=value_style,
        textColor=HexColor("#60716d"),
        fontName="Helvetica-Bold",
    )
    small_style = ParagraphStyle(
        "SmallCustom",
        parent=styles["Normal"],
        fontSize=8,
        textColor=HexColor("#60716d"),
        spaceBefore=4 * mm,
    )

    elements: list = []
    elements.append(Paragraph("Anamnese-Zusammenfassung", title_style))

    scenario_text = get_scenario_title(summary.scenario) if summary.scenario else ""
    timestamp = summary.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append(
        Paragraph(f"Szenario: {scenario_text}<br/>Erstellt: {timestamp}", small_style)
    )
    elements.append(HRFlowable(width="100%", color=accent_color))
    elements.append(Spacer(1, 4 * mm))

    patient_name = f"{patient.first_name} {patient.last_name}"
    _add_section(
        elements,
        "Patientendaten",
        [
            ("Name", patient_name),
            ("Patienten-ID", patient.patient_id),
            ("Geburtsdatum", patient.date_of_birth),
            ("Vorerkrankungen", patient.conditions or "keine"),
            (
                "Medikamente",
                ", ".join(patient.medications) if patient.medications else "keine",
            ),
        ],
        label_style,
        value_style,
        doc.width,
    )

    if summary.red_flags:
        _add_red_flags_section(
            elements,
            summary.red_flags,
            heading_style,
            label_style,
            value_style,
            severity_critical_style,
            severity_warning_style,
            severity_info_style,
            doc.width,
        )

    if summary.grouped_sections:
        for title, fields in summary.grouped_sections.items():
            _add_section(
                elements,
                title,
                list(fields.items()),
                label_style,
                value_style,
                doc.width,
            )
    else:
        _add_section(
            elements,
            "Anamnese-Antworten",
            list(summary.answers.items()),
            label_style,
            value_style,
            doc.width,
        )

    vitals_rows = _vital_rows(summary)
    _add_section(
        elements,
        "Vitalparameter",
        vitals_rows,
        label_style,
        value_style,
        doc.width,
    )

    if summary.open_points:
        elements.append(Paragraph("Offene Punkte", heading_style))
        for point in summary.open_points:
            elements.append(Paragraph(f"&bull; {escape(str(point))}", value_style))

    doc.build(elements)
    return buf.getvalue()


def _add_red_flags_section(
    elements: list[Any],
    red_flags: list[Any],
    heading_style: "ParagraphStyle",
    label_style: "ParagraphStyle",
    value_style: "ParagraphStyle",
    severity_critical_style: "ParagraphStyle",
    severity_warning_style: "ParagraphStyle",
    severity_info_style: "ParagraphStyle",
    available_width: float,
) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import Paragraph, Table, TableStyle

    elements.append(Paragraph("Red Flags", heading_style))
    table_data = [
        [
            _wrap_pdf_cell("ID", label_style),
            _wrap_pdf_cell("Schwere", label_style),
            _wrap_pdf_cell("Beschreibung", label_style),
        ]
    ]
    for red_flag in red_flags:
        table_data.append(
            [
                _wrap_pdf_cell(red_flag.rule_id, value_style),
                _wrap_pdf_cell(
                    _severity_label(red_flag.severity),
                    _severity_pdf_style(
                        red_flag.severity,
                        severity_critical_style,
                        severity_warning_style,
                        severity_info_style,
                    ),
                ),
                _wrap_pdf_cell(red_flag.description, value_style),
            ]
        )

    table = Table(
        table_data,
        colWidths=[available_width * 0.15, available_width * 0.17, available_width * 0.68],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f0f0f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#e0e0e0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(table)


def _add_section(
    elements: list[Any],
    title: str,
    rows: list[tuple[str, str]],
    label_style: "ParagraphStyle",
    value_style: "ParagraphStyle",
    available_width: float,
) -> None:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, Spacer, Table, TableStyle

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=label_style,
        textColor=HexColor("#17342f"),
        fontSize=11,
        fontName="Helvetica-Bold",
        spaceBefore=6 * mm,
        spaceAfter=2 * mm,
    )
    elements.append(Paragraph(title, section_heading))
    elements.append(HRFlowable(width="100%", color=HexColor("#e0e0e0")))
    elements.append(Spacer(1, 2 * mm))

    table_data = []
    for label, value in rows:
        display_value = str(value) if value and str(value).strip() else "keine Angabe"
        table_data.append(
            [
                _wrap_pdf_cell(label, label_style),
                _wrap_pdf_cell(display_value, value_style),
            ]
        )

    if table_data:
        tbl = Table(
            table_data,
            colWidths=[available_width * 0.29, available_width * 0.71],
        )
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#eeeeee")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(tbl)

    elements.append(Spacer(1, 2 * mm))


def _wrap_pdf_cell(value: Any, style: "ParagraphStyle") -> Any:
    from reportlab.platypus import Paragraph

    text = escape(str(value)).replace("\n", "<br/>")
    return Paragraph(text, style)


def _severity_text_color(severity: str) -> str:
    return SEVERITY_TEXT_COLORS.get(severity.lower(), SEVERITY_TEXT_COLORS["info"])


def _severity_pdf_style(
    severity: str,
    critical_style: "ParagraphStyle",
    warning_style: "ParagraphStyle",
    info_style: "ParagraphStyle",
) -> "ParagraphStyle":
    if severity.lower() == "critical":
        return critical_style
    if severity.lower() == "warning":
        return warning_style
    return info_style


def _severity_label(severity: str) -> str:
    mapping = {
        "critical": "KRITISCH",
        "warning": "WARNUNG",
        "info": "INFO",
    }
    return mapping.get(severity.lower(), severity.upper())
