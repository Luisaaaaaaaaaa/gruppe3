import re
import zlib
import base64

from app.medical_rules.red_flag_engine import RedFlag
from app.output.export_pdf import export_summary_pdf
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
