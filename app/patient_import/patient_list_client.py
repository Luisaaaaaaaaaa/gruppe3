import json
import re
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
            medikation = patient.get("medizinische_uebersicht", {}).get("medikation", {})
            medications = self._extract_medication_names(medikation)
            patients.append(
                PatientRecord(
                    patient_id=patient["patient_id"],
                    first_name=master_data["vorname"],
                    last_name=master_data["nachname"],
                    date_of_birth=master_data["geburtsdatum"],
                    medications=medications,
                )
            )

        return patients

    @staticmethod
    def _extract_medication_names(medikation: dict) -> list[str]:
        names: list[str] = []

        for entry in medikation.get("dauermedikation", []):
            name = _extract_brand_name(entry.get("praeparat", ""))
            if name:
                names.append(name)

        for entry in medikation.get("bedarfsmedikation", []):
            name = _extract_brand_name(entry.get("praeparat", ""))
            if name:
                names.append(name)

        return names


def _extract_brand_name(praeparat: str) -> str:
    """Extrahiert den Handelsnamen ohne Dosierung aus der Präparatbezeichnung.
    Z.B. 'Metformin 1000 mg Filmtabletten' -> 'Metformin'
         'Bisoprolol 2,5 mg Tabletten' -> 'Bisoprolol'
         'Paracetamol 500 mg Tabletten' -> 'Paracetamol'
    """
    name = praeparat.strip()
    # Alles ab der ersten Ziffer (mit optionalem Komma/Punkt für Dezimaltrenner) entfernen
    name = re.sub(r"\s+\d+[.,]?\d*\s*(mg|g|µg|mcg|ml|ie|i\.e\.).*", "", name, flags=re.IGNORECASE)
    name = name.strip()
    return name
