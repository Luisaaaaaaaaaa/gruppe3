"""Unit-Tests fuer Patientenlisten-Import und Schema-Validierung."""

import json

import pytest

from app.patient_import.patient_list_client import PatientListClient
from app.patient_import.patient_schema import PatientRecord


class TestPatientListClient:
    def _write_json(self, tmp_path, data):
        path = tmp_path / "patients.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_load_valid_patients(self, tmp_path) -> None:
        data = [
            {
                "patient": {
                    "patient_id": "P-001",
                    "status": "aktiv",
                    "stammdaten": {
                        "vorname": "Anna",
                        "nachname": "Muster",
                        "geburtsdatum": "1985-03-14",
                        "geschlecht": "weiblich",
                        "sprache": "de",
                    },
                    "kontakt": {"adresse": {"ort": "Mannheim"}},
                    "versicherung": {"krankenkasse": {"name": "AOK Test"}},
                    "administrativ": {"patientenhinweise": ["Nuechtern erscheinen"]},
                    "medizinische_uebersicht": {
                        "allergien": [
                            {"substanz": "Penicillin", "schweregrad": "mittel"}
                        ],
                        "risikofaktoren": {
                            "bmi": 28.4,
                            "rauchen": "nie",
                            "alkohol": "gelegentlich",
                            "familienanamnese": ["Vater: Hypertonie"],
                        },
                        "dauerdiagnosen": [
                            {"bezeichnung": "Hypertonie", "icd10": "I10"}
                        ],
                        "akutdiagnosen": [
                            {"bezeichnung": "Infekt", "icd10": "J06.9"}
                        ],
                        "medikation": {
                            "dauermedikation": [
                                {
                                    "praeparat": "Ramipril 5 mg Tabletten",
                                    "dosierung": "1-0-0",
                                }
                            ]
                        },
                    },
                    "termine": {
                        "naechster_termin": {
                            "datum_uhrzeit": "2026-07-20T08:15:00+02:00",
                            "art": "Kontrolle",
                            "hinweis": "Bitte nuechtern kommen",
                        },
                        "offene_aufgaben": [
                            {
                                "faellig_am": "2026-07-20",
                                "aufgabe": "Labor kontrollieren",
                                "prioritaet": "normal",
                            }
                        ],
                    },
                }
            },
            {
                "patient": {
                    "patient_id": "P-002",
                    "stammdaten": {
                        "vorname": "Max",
                        "nachname": "Mustermann",
                        "geburtsdatum": "1970-11-22",
                    },
                }
            },
        ]
        path = self._write_json(tmp_path, data)
        client = PatientListClient(path)
        patients = client.load_patients()

        assert len(patients) == 2
        assert patients[0].patient_id == "P-001"
        assert patients[0].first_name == "Anna"
        assert patients[0].last_name == "Muster"
        assert patients[0].date_of_birth == "1985-03-14"
        assert patients[0].medications == ["Ramipril"]
        assert patients[0].details.gender == "weiblich"
        assert patients[0].details.contact_city == "Mannheim"
        assert patients[0].details.insurance == "AOK Test"
        assert patients[0].details.long_term_diagnoses == ("Hypertonie (I10)",)
        assert patients[0].details.acute_diagnoses == ("Infekt (J06.9)",)
        assert patients[0].details.allergies == ("Penicillin (mittel)",)
        assert patients[0].details.patient_notes == ("Nuechtern erscheinen",)
        assert patients[0].details.open_tasks == (
            "Labor kontrollieren - faellig 2026-07-20 - Prioritaet normal",
        )

    def test_load_empty_list(self, tmp_path) -> None:
        path = self._write_json(tmp_path, [])
        client = PatientListClient(path)
        patients = client.load_patients()
        assert patients == []

    def test_missing_patient_id_raises(self, tmp_path) -> None:
        data = [
            {
                "patient": {
                    "stammdaten": {
                        "vorname": "Test",
                        "nachname": "User",
                        "geburtsdatum": "2000-01-01",
                    },
                }
            }
        ]
        path = self._write_json(tmp_path, data)
        client = PatientListClient(path)
        with pytest.raises(KeyError):
            client.load_patients()

    def test_missing_stammdaten_raises(self, tmp_path) -> None:
        data = [{"patient": {"patient_id": "P-001"}}]
        path = self._write_json(tmp_path, data)
        client = PatientListClient(path)
        with pytest.raises(KeyError):
            client.load_patients()

    def test_invalid_json_raises(self, tmp_path) -> None:
        path = tmp_path / "patients.json"
        path.write_text("not valid json{{{", encoding="utf-8")
        client = PatientListClient(path)
        with pytest.raises(json.JSONDecodeError):
            client.load_patients()

    def test_file_not_found_raises(self, tmp_path) -> None:
        path = tmp_path / "nonexistent.json"
        client = PatientListClient(path)
        with pytest.raises(FileNotFoundError):
            client.load_patients()


class TestPatientRecord:
    def test_creation(self) -> None:
        record = PatientRecord(
            patient_id="P-001",
            first_name="Anna",
            last_name="Muster",
            date_of_birth="1985-03-14",
        )
        assert record.patient_id == "P-001"
        assert record.first_name == "Anna"
        assert record.last_name == "Muster"
        assert record.date_of_birth == "1985-03-14"

    def test_is_frozen(self) -> None:
        record = PatientRecord(
            patient_id="P-001",
            first_name="Anna",
            last_name="Muster",
            date_of_birth="1985-03-14",
        )
        with pytest.raises(Exception):
            record.patient_id = "changed"
