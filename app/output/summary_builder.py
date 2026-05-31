from dataclasses import dataclass, field
from datetime import datetime

from app.medical_rules.red_flag_engine import RedFlag
from app.patient_import.patient_schema import PatientRecord


@dataclass
class AnamnesisSummary:
    patient_id: str
    patient_name: str
    scenario: str
    timestamp: str
    answers: dict[str, str] = field(default_factory=dict)
    vitals: dict[str, int | float] = field(default_factory=dict)
    vitals_source: str = "simuliert"
    red_flags: list[RedFlag] = field(default_factory=list)
    escalation_required: bool = False
    open_points: list[str] = field(default_factory=list)
    grouped_sections: dict[str, dict[str, str]] = field(default_factory=dict)
    synthetic: bool = True


def build_summary(
    patient: PatientRecord,
    scenario: str,
    answers: dict[str, str],
    vitals: dict[str, int | float] | None,
    vitals_source: str,
    red_flags: list[RedFlag],
) -> AnamnesisSummary:
    has_critical = any(rf.severity == "critical" for rf in red_flags)

    open_points: list[str] = []
    for key, value in answers.items():
        if not value.strip() or value.strip().lower() == "unbekannt":
            open_points.append(f"Angabe zu '{key}' fehlt oder unbekannt.")

    grouped_sections = build_grouped_sections(scenario, answers, vitals or {})

    return AnamnesisSummary(
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        scenario=scenario,
        timestamp=datetime.now().isoformat(timespec="seconds"),
        answers=answers,
        vitals=vitals or {},
        vitals_source=vitals_source,
        red_flags=red_flags,
        escalation_required=has_critical,
        open_points=open_points,
        grouped_sections=grouped_sections,
    )


def build_grouped_sections(
    scenario: str,
    answers: dict[str, str],
    vitals: dict[str, int | float],
) -> dict[str, dict[str, str]]:
    if scenario not in ("D", "diabetes"):
        return {}

    return {
        "Verlauf": {
            "Aktuelles Gewicht": answers.get("gewicht_aktuell", ""),
            "Gewichtsveraenderung": (
                answers.get("gewichtsveraenderung_details", "")
                if answers.get("gewichtsveraenderung", "").strip().lower() in ("ja", "j", "yes", "y")
                else "keine angegeben"
            ),
            "Blutdruck": (
                f"{answers.get('blutdruck_systolisch', '').strip() or vitals.get('systolisch', 'unbekannt')}/"
                f"{answers.get('blutdruck_diastolisch', '').strip() or vitals.get('diastolisch', 'unbekannt')} mmHg"
            ),
            "Letzte Diabetes-Kontrolle": answers.get("letzte_kontrolle", ""),
        },
        "Aktuelle Symptome": {
            "Hinweise auf Hypo-/Hyperglykaemie": answers.get("hypo_hyper_hinweise", ""),
            "Beschwerden": answers.get("hypo_hyper_beschwerden", ""),
        },
        "Medikation": {
            "Aktuelle Medikamente": answers.get("medikamente", ""),
            "Bekannte Diagnosen": answers.get("bekannte_diagnosen", ""),
        },
        "Komplikationen": {
            "Folgeerkrankungen bekannt": answers.get("folgeerkrankungen_bekannt", ""),
            "Details": answers.get("folgeerkrankungen_details", ""),
            "Fussprobleme oder Wunden": answers.get("offene_wunde_fussproblem", ""),
            "Fussproblem-Details": answers.get("offene_wunde_fussproblem_details", ""),
        },
        "Vorbefunde": {
            "HbA1c bekannt": answers.get("hba1c_bekannt", ""),
            "HbA1c-Wert": answers.get("hba1c_wert", ""),
            "Blutzuckerwert bekannt": answers.get("blutzuckerwert_bekannt", ""),
            "Blutzuckerwert": answers.get("blutzuckerwert_details", ""),
        },
        "Offene Fragen": {
            "Patientenfragen": answers.get("offene_fragen", ""),
            "Lebensstil": answers.get("lebensstil", ""),
        },
    }
