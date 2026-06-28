import re
import zlib
import base64

from app.medical_rules.red_flag_engine import RedFlag
from app.output.export_pdf import build_preview_html, export_summary_pdf
from app.output.summary_builder import AnamnesisSummary
from app.patient_import.patient_schema import PatientRecord


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    text = pdf_bytes.decode("latin-1")
    streams = re.findall(r"stream\n(.+?)\n?endstream", text, re.DOTALL)
    result = ""
    for s in streams:
        raw = s.strip()
        try:
            dec_a85 = base64.a85decode(raw.encode("ascii"), adobe=True)
        except Exception:
            try:
                dec_a85 = zlib.decompress(raw.encode("latin-1"))
            except zlib.error:
                continue
            else:
                result += dec_a85.decode("latin-1", errors="replace")
                continue
        try:
            dec = zlib.decompress(dec_a85)
        except zlib.error:
            result += dec_a85.decode("latin-1", errors="replace")
        else:
            result += dec.decode("latin-1", errors="replace")
    return result


def test_export_summary_pdf_returns_pdf_bytes_with_key_content() -> None:
    patient = PatientRecord(
        patient_id="P-4711",
        first_name="Erika",
        last_name="Mustermann",
        date_of_birth="1972-04-19",
        medications=["Metformin", "Ramipril"],
        conditions="Diabetes mellitus Typ 2",
    )
    summary = AnamnesisSummary(
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        scenario="diabetes",
        timestamp="2026-06-16T16:30:00",
        answers={"offene_fragen": "Frage zum HbA1c"},
        vitals={"systolisch": 182, "diastolisch": 101},
        vitals_source="simuliert",
        red_flags=[
            RedFlag(
                rule_id="DM-RF-009",
                description="Systolischer Blutdruck >= 180 mmHg im Diabetes-Szenario: Kritischer Blutdruckwert.",
                severity="critical",
                triggered_by="systolisch=182",
            )
        ],
        escalation_required=True,
        open_points=["Angabe zu 'gewicht_aktuell' fehlt oder unbekannt."],
        grouped_sections={
            "Verlauf": {
                "Aktuelles Gewicht": "keine Angabe",
                "Blutdruck": "182/101 mmHg",
            }
        },
    )

    pdf_bytes = export_summary_pdf(summary, patient)

    assert pdf_bytes.startswith(b"%PDF-1.4")
    pdf_text = _extract_pdf_text(pdf_bytes)
    assert "Erika Mustermann" in pdf_text
    assert "P-4711" in pdf_text
    assert "KRITISCH" in pdf_text
    assert pdf_text.index("Patientendaten") < pdf_text.index("Red Flags")
    assert pdf_text.index("Red Flags") < pdf_text.index("Verlauf")


def test_preview_documents_source_for_each_vital() -> None:
    patient = PatientRecord(patient_id="P-1", first_name="Test", last_name="Person")
    summary = AnamnesisSummary(
        patient_id="P-1",
        patient_name="Test Person",
        scenario="C",
        timestamp="2026-06-20T12:00:00",
        vitals={"systolisch": 145, "gewicht": 78},
        vital_sources={
            "systolisch": "simuliert",
            "gewicht": "manuell eingegeben",
        },
    )

    html = build_preview_html(summary, patient)

    assert "145 (Quelle: simuliert)" in html
    assert "78 (Quelle: manuell eingegeben)" in html


def test_export_summary_pdf_handles_very_long_table_values() -> None:
    patient = PatientRecord(
        patient_id="P-LANG",
        first_name="Lange",
        last_name="Antwort",
        date_of_birth="1980-01-01",
        medications=[
            "Sehr langes Praeparat mit vielen Details und Dosierungshinweisen",
        ],
        conditions="Hypertonie mit sehr langer Beschreibung der Begleiterkrankungen",
    )
    long_text = (
        "Patient berichtet ueber seit mehreren Wochen bestehende Beschwerden "
        "mit sehr ausfuehrlicher Beschreibung, inklusive freiem Text, "
        "Medikationsdetails und einem langen ununterbrochenen Testwort "
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789."
    )
    summary = AnamnesisSummary(
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        scenario="hypertension",
        timestamp="2026-06-20T12:00:00",
        answers={"sehr_lange_antwort": long_text},
        red_flags=[
            RedFlag(
                rule_id="RF-SEHR-LANGE-ID-1234567890",
                description=long_text,
                severity="warning",
                triggered_by="test",
            )
        ],
    )

    pdf_bytes = export_summary_pdf(summary, patient)

    assert pdf_bytes.startswith(b"%PDF-1.4")


def test_export_summary_pdf_marks_red_flag_severities() -> None:
    patient = PatientRecord(patient_id="P-RF", first_name="Red", last_name="Flag")
    summary = AnamnesisSummary(
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        scenario="cough",
        timestamp="2026-06-20T12:00:00",
        red_flags=[
            RedFlag(
                rule_id="RF-CRIT",
                description="Kritische Beschreibung",
                severity="critical",
                triggered_by="test",
            ),
            RedFlag(
                rule_id="RF-WARN",
                description="Warnende Beschreibung",
                severity="warning",
                triggered_by="test",
            ),
        ],
    )

    pdf_bytes = export_summary_pdf(summary, patient)
    pdf_text = _extract_pdf_text(pdf_bytes)

    assert "KRITISCH" in pdf_text
    assert "WARNUNG" in pdf_text
    assert ".623529 .113725 .12549 rg" in pdf_text
    assert ".709804 .352941 .027451 rg" in pdf_text


def test_preview_tables_wrap_long_content() -> None:
    patient = PatientRecord(patient_id="P-1", first_name="Test", last_name="Person")
    summary = AnamnesisSummary(
        patient_id="P-1",
        patient_name="Test Person",
        scenario="C",
        timestamp="2026-06-20T12:00:00",
        answers={"lange_antwort": "A" * 120},
    )

    html = build_preview_html(summary, patient)

    assert "table-layout: fixed" in html
    assert "overflow-wrap: anywhere" in html
