import json
import re
from pathlib import Path

from app.patient_import.patient_schema import PatientDetails, PatientRecord


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
            details = self._build_patient_details(patient)
            patients.append(
                PatientRecord(
                    patient_id=patient["patient_id"],
                    first_name=master_data["vorname"],
                    last_name=master_data["nachname"],
                    date_of_birth=master_data["geburtsdatum"],
                    medications=medications,
                    conditions=conditions,
                    details=details,
                )
            )

        return patients

    def _build_patient_details(self, patient: dict) -> PatientDetails:
        master_data = patient.get("stammdaten", {})
        kontakt = patient.get("kontakt", {})
        adresse = kontakt.get("adresse", {})
        versicherung = patient.get("versicherung", {})
        krankenkasse = versicherung.get("krankenkasse", {})
        uebersicht = patient.get("medizinische_uebersicht", {})
        medikation = uebersicht.get("medikation", {})
        administrativ = patient.get("administrativ", {})
        termine = patient.get("termine", {})
        next_appointment = termine.get("naechster_termin") or {}

        return PatientDetails(
            status=patient.get("status", ""),
            gender=master_data.get("geschlecht", ""),
            language=master_data.get("sprache", ""),
            contact_city=adresse.get("ort", ""),
            insurance=krankenkasse.get("name", ""),
            next_appointment_at=next_appointment.get("datum_uhrzeit", ""),
            next_appointment_type=next_appointment.get("art", ""),
            next_appointment_note=next_appointment.get("hinweis", ""),
            allergies=tuple(self._extract_allergies(uebersicht)),
            long_term_diagnoses=tuple(
                self._extract_diagnoses(uebersicht.get("dauerdiagnosen", []))
            ),
            acute_diagnoses=tuple(
                self._extract_diagnoses(uebersicht.get("akutdiagnosen", []))
            ),
            risk_factors=tuple(
                self._extract_risk_factors(uebersicht.get("risikofaktoren", {}))
            ),
            medication_details=tuple(self._extract_medication_details(medikation)),
            patient_notes=tuple(administrativ.get("patientenhinweise", [])),
            open_tasks=tuple(
                self._extract_open_tasks(termine.get("offene_aufgaben", []))
            ),
        )

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

    @staticmethod
    def _extract_allergies(uebersicht: dict) -> list[str]:
        allergies: list[str] = []
        for entry in uebersicht.get("allergien", []):
            substance = entry.get("substanz")
            if not substance:
                continue
            severity = entry.get("schweregrad")
            allergies.append(f"{substance} ({severity})" if severity else substance)
        return allergies

    @staticmethod
    def _extract_diagnoses(entries: list[dict]) -> list[str]:
        diagnoses: list[str] = []
        for entry in entries:
            label = entry.get("bezeichnung")
            if not label:
                continue
            icd10 = entry.get("icd10")
            diagnoses.append(f"{label} ({icd10})" if icd10 else label)
        return diagnoses

    @staticmethod
    def _extract_risk_factors(risk: dict) -> list[str]:
        items: list[str] = []
        bmi = risk.get("bmi")
        if bmi:
            items.append(f"BMI {bmi}")
        smoking = risk.get("rauchen")
        if smoking:
            items.append(f"Rauchen: {smoking}")
        alcohol = risk.get("alkohol")
        if alcohol:
            items.append(f"Alkohol: {alcohol}")
        for family_history in risk.get("familienanamnese", []):
            items.append(f"Familienanamnese: {family_history}")
        return items

    @staticmethod
    def _extract_medication_details(medikation: dict) -> list[str]:
        details: list[str] = []
        for section_label, entries in (
            ("Dauer", medikation.get("dauermedikation", [])),
            ("Bedarf", medikation.get("bedarfsmedikation", [])),
        ):
            for entry in entries:
                label = entry.get("praeparat") or entry.get("wirkstoff")
                if not label:
                    continue
                dosage = entry.get("dosierung")
                if dosage:
                    details.append(f"{section_label}: {label} - {dosage}")
                else:
                    details.append(f"{section_label}: {label}")
        return details

    @staticmethod
    def _extract_open_tasks(entries: list[dict]) -> list[str]:
        tasks: list[str] = []
        for entry in entries:
            label = entry.get("aufgabe")
            if not label:
                continue
            due_date = entry.get("faellig_am")
            priority = entry.get("prioritaet")
            parts = [label]
            if due_date:
                parts.append(f"faellig {due_date}")
            if priority:
                parts.append(f"Prioritaet {priority}")
            tasks.append(" - ".join(parts))
        return tasks


    def append_patient(self, patient: PatientRecord) -> None:
        patients = self.load_patients()
        for i, p in enumerate(patients):
            if p.patient_id == patient.patient_id:
                patients[i] = patient
                break
        else:
            patients.append(patient)
        self._save_patients(patients)

    def _save_patients(self, patients: list[PatientRecord]) -> None:
        entries = []
        for rec in patients:
            entry = self._record_to_entry(rec)
            entries.append(entry)
        self._json_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _record_to_entry(rec: PatientRecord) -> dict:
        return {
            "schema_version": "1.0",
            "source_system": {"name": "SET-Anamnese", "version": "1.0"},
            "patient": {
                "patient_id": rec.patient_id,
                "status": rec.details.status or "aktiv",
                "stammdaten": {
                    "vorname": rec.first_name,
                    "nachname": rec.last_name,
                    "geburtsdatum": rec.date_of_birth,
                    "geschlecht": rec.details.gender,
                    "sprache": rec.details.language,
                },
                "kontakt": {
                    "adresse": {
                        "ort": rec.details.contact_city,
                    },
                    "telefon": rec.details.phone,
                },
                "versicherung": {
                    "krankenkasse": {"name": rec.details.insurance},
                },
                "administrativ": {
                    "patientenhinweise": [rec.details.notes] if rec.details.notes else [],
                },
                "medizinische_uebersicht": {
                    "allergien": [],
                    "risikofaktoren": {},
                    "dauerdiagnosen": [],
                    "akutdiagnosen": [],
                    "medikation": {"dauermedikation": [], "bedarfsmedikation": []},
                },
                "termine": {
                    "naechster_termin": None,
                    "offene_aufgaben": [],
                },
            },
        }


def _extract_brand_name(praeparat: str) -> str:
    name = praeparat.strip()
    name = re.sub(r"\s+\d+[.,]?\d*\s*(mg|g|µg|mcg|ml|ie|i\.e\.).*", "", name, flags=re.IGNORECASE)
    name = name.strip()
    return name
