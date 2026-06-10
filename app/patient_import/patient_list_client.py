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
            uebersicht = patient.get("medizinische_uebersicht", {})
            medikation = uebersicht.get("medikation", {})
            medications = self._extract_medication_names(medikation)
            conditions = self._build_conditions_string(uebersicht)
            patients.append(
                PatientRecord(
                    patient_id=patient["patient_id"],
                    first_name=master_data["vorname"],
                    last_name=master_data["nachname"],
                    date_of_birth=master_data["geburtsdatum"],
                    medications=medications,
                    conditions=conditions,
                )
            )

        return patients

    @staticmethod
    def _build_conditions_string(uebersicht: dict) -> str:
        parts: list[str] = []

        diagnosed = uebersicht.get("dauerdiagnosen", [])
        if diagnosed:
            names = [
                f"{d['bezeichnung']} ({d['icd10']})"
                for d in diagnosed
                if d.get("bezeichnung")
            ]
            parts.append("Dauerdiagnosen: " + ", ".join(names))

        risk = uebersicht.get("risikofaktoren", {})
        risk_items: list[str] = []
        if risk.get("bmi"):
            risk_items.append(f"BMI {risk['bmi']}")
        rauchen = risk.get("rauchen", "")
        if rauchen:
            risk_items.append(f"Rauchen: {rauchen}")
        alkohol = risk.get("alkohol", "")
        if alkohol:
            risk_items.append(f"Alkohol: {alkohol}")
        familien = risk.get("familienanamnese", [])
        if familien:
            risk_items.append("Familienanamnese: " + "; ".join(familien))
        if risk_items:
            parts.append("Risikofaktoren: " + ". ".join(risk_items))

        allergies = uebersicht.get("allergien", [])
        if allergies:
            items = [
                f"{a['substanz']} ({a.get('schweregrad', 'nicht angegeben')})"
                for a in allergies
                if a.get("substanz")
            ]
            parts.append("Allergien: " + ", ".join(items))

        return ". ".join(parts)

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
