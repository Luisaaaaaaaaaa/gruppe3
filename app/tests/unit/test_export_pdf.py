from app.medical_rules.red_flag_engine import RedFlag
from app.output.export_pdf import export_summary_pdf
from app.output.summary_builder import AnamnesisSummary
from app.patient_import.patient_schema import PatientRecord


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
    assert b"Erika Mustermann" in pdf_bytes
    assert b"P-4711" in pdf_bytes
    assert b"Risikopunkte" in pdf_bytes
    assert b"KRITISCH" in pdf_bytes
