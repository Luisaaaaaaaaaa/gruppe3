import json
from pathlib import Path

from app.patient_import.patient_schema import PatientRecord


class PatientListClient:
    def __init__(self, json_path: Path) -> None:
        self._json_path = json_path

    def load_patients(self) -> list[PatientRecord]:
        raw_data = json.loads(self._json_path.read_text(encoding="utf-8"))
        patients: list[PatientRecord] = []

        for entry in raw_data:
            patient = entry.get("patient", {})
            master_data = patient.get("stammdaten", {})
            patients.append(
                PatientRecord(
                    patient_id=patient["patient_id"],
                    first_name=master_data["vorname"],
                    last_name=master_data["nachname"],
                    date_of_birth=master_data["geburtsdatum"],
                )
            )

        return patients
