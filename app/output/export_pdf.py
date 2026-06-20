from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any

from app.output.summary_builder import AnamnesisSummary
from app.patient_import.patient_schema import PatientRecord

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

    if summary.grouped_sections:
        for title, fields in summary.grouped_sections.items():
            items = list(fields.items())
            html_parts.append(_html_section(title, items))
    else:
        html_parts.append(_html_section("Anamnese-Antworten", list(summary.answers.items())))

    vitals_rows = [("Quelle", summary.vitals_source or "simuliert")]
    vitals_rows.extend(
        (key, str(value)) for key, value in summary.vitals.items()
    )
    html_parts.append(_html_section("Vitalparameter", vitals_rows))

    if summary.red_flags:
        rf_rows = [
            '<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">'
            '<tr style="background:#f0f0f0"><th>ID</th><th>Schwere</th><th>Beschreibung</th></tr>'
        ]
        for rf in summary.red_flags:
            rf_rows.append(
                f"<tr><td>{rf.rule_id}</td><td>{rf.severity}</td><td>{rf.description}</td></tr>"
            )
        rf_rows.append("</table>")
        html_parts.append(
            _html_section_raw("Red Flags", "".join(rf_rows))
        )

    if summary.open_points:
        items = "".join(f"<li>{p}</li>" for p in summary.open_points)
        html_parts.append(
            _html_section_raw("Offene Punkte", f"<ul>{items}</ul>")
        )

    scenario_text = f"{summary.scenario} &mdash; " if summary.scenario else ""
    timestamp = summary.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")

    return (
        '<!DOCTYPE html>\n<html lang="de">\n<head><meta charset="utf-8">\n'
        "<style>\n"
        "  body { font-family: 'Segoe UI', Arial, sans-serif; color: #17342f; margin: 30px; }\n"
        "  h1 { color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 6px; }\n"
        "  h2 { color: #17342f; margin-top: 20px; }\n"
        "  table { border-collapse: collapse; width: 100%; margin: 8px 0; }\n"
        "  td, th { padding: 6px 10px; text-align: left; border: 1px solid #ddd; }\n"
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
            Table,
            TableStyle,
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
        fontSize=8,
        spaceAfter=1 * mm,
    )
    value_style = ParagraphStyle(
        "ValueCustom",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=2 * mm,
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

    scenario_text = summary.scenario or ""
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
    )

    if summary.grouped_sections:
        for title, fields in summary.grouped_sections.items():
            _add_section(
                elements,
                title,
                list(fields.items()),
                label_style,
                value_style,
            )
    else:
        _add_section(
            elements,
            "Anamnese-Antworten",
            list(summary.answers.items()),
            label_style,
            value_style,
        )

    vitals_rows = [("Quelle", summary.vitals_source or "simuliert")]
    vitals_rows.extend(
        (key, str(value)) for key, value in summary.vitals.items()
    )
    _add_section(elements, "Vitalparameter", vitals_rows, label_style, value_style)

    if summary.red_flags:
        elements.append(Paragraph("Red Flags", heading_style))
        rf_data = [["ID", "Schwere", "Beschreibung"]]
        for rf in summary.red_flags:
            rf_data.append([rf.rule_id, _severity_label(rf.severity), rf.description])

        rf_colors = []
        for rf in summary.red_flags:
            if rf.severity == "critical":
                rf_colors.append(danger_color)
            elif rf.severity == "warning":
                rf_colors.append(warning_color)
            else:
                rf_colors.append(HexColor("#60716d"))

        rf_table = Table(rf_data, colWidths=[50, 50, 380])
        rf_table.setStyle(
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
        for idx, color in enumerate(rf_colors):
            rf_table.setStyle(
                TableStyle(
                    [
                        (
                            "TEXTCOLOR",
                            (1, idx + 1),
                            (1, idx + 1),
                            color,
                        ),
                        ("FONTNAME", (1, idx + 1), (1, idx + 1), "Helvetica-Bold"),
                    ]
                )
            )
        elements.append(rf_table)

    if summary.open_points:
        elements.append(Paragraph("Offene Punkte", heading_style))
        for point in summary.open_points:
            elements.append(Paragraph(f"&bull; {point}", value_style))

    doc.build(elements)
    return buf.getvalue()


def _add_section(
    elements: list[Any],
    title: str,
    rows: list[tuple[str, str]],
    label_style: "ParagraphStyle",
    value_style: "ParagraphStyle",
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
        display_value = value if value and value.strip() else "keine Angabe"
        table_data.append([label, display_value])

    if table_data:
        tbl = Table(table_data, colWidths=[120, 330])
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


def _severity_label(severity: str) -> str:
    mapping = {
        "critical": "KRITISCH",
        "warning": "WARNUNG",
        "info": "INFO",
    }
    return mapping.get(severity.lower(), severity.upper())
