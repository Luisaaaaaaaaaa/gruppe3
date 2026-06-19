from __future__ import annotations

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
    vitals: dict | None = None,
    vitals_source: str = "simuliert",
    red_flags: list[RedFlag] | None = None,
) -> AnamnesisSummary:
    if red_flags is None:
        red_flags = []

    if vitals is None:
        vitals = {}

    escalation_required = any(rf.severity == "critical" for rf in red_flags)

    _ignored_keys = frozenset({
        "blutdruck_messen",
        "blutdruck_diastolisch",
        "puls_messen",
        "gewicht_messen",
    })

    open_points = [
        f"Angabe zu '{key}' fehlt oder unbekannt."
        for key, value in answers.items()
        if key not in _ignored_keys
        and (not value.strip() or value.strip().lower() == "unbekannt")
    ]

    grouped_sections = build_grouped_sections(scenario, answers, vitals)

    return AnamnesisSummary(
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        scenario=scenario,
        timestamp=datetime.now().isoformat(),
        answers=answers,
        vitals=vitals,
        vitals_source=vitals_source,
        red_flags=red_flags,
        escalation_required=escalation_required,
        open_points=open_points,
        grouped_sections=grouped_sections,
    )


def build_grouped_sections(
    scenario: str, answers: dict[str, str], vitals: dict
) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}

    if answers.get("vorerkrankungen_aktuell", "").strip():
        sections["Vorerkrankungen / Risikofaktoren (aktueller Stand)"] = {
            "Allgemein": answers.get("vorerkrankungen_aktuell", "")
        }

    if scenario in ("D", "diabetes"):
        verlauf: dict[str, str] = {}

        gewicht = answers.get("gewicht_aktuell", "").strip()
        if gewicht and gewicht.lower() != "unbekannt":
            verlauf["Aktuelles Gewicht"] = f"{gewicht} kg"
        else:
            verlauf["Aktuelles Gewicht"] = "keine Angabe"

        gv = answers.get("gewichtsveraenderung", "").strip().lower()
        if gv in ("ja", "j", "yes", "y"):
            gv_details = answers.get("gewichtsveraenderung_details", "").strip()
            verlauf["Gewichtsveraenderung"] = gv_details if gv_details else "ja"
        else:
            verlauf["Gewichtsveraenderung"] = "keine angegeben"

        sys_val = answers.get("blutdruck_systolisch", "").strip()
        dia_val = answers.get("blutdruck_diastolisch", "").strip()

        if sys_val.lower() != "unbekannt" and sys_val:
            sys_str = sys_val
        elif "systolisch" in vitals:
            sys_str = str(vitals["systolisch"])
        else:
            sys_str = "unbekannt"

        if dia_val.lower() != "unbekannt" and dia_val:
            dia_str = dia_val
        elif "diastolisch" in vitals:
            dia_str = str(vitals["diastolisch"])
        else:
            dia_str = "unbekannt"

        verlauf["Blutdruck"] = f"{sys_str}/{dia_str} mmHg"

        verlauf["Letzte Diabetes-Kontrolle"] = answers.get("letzte_kontrolle", "")

        sections["Verlauf"] = verlauf

        symptome: dict[str, str] = {}
        hypo_val = answers.get("hypo_hyper_hinweise", "")
        if hypo_val:
            symptome["Hinweise auf Hypo-/Hyperglykaemie"] = hypo_val
        hypo_details = answers.get("hypo_hyper_beschwerden", "")
        if hypo_details:
            symptome["Beschwerden"] = hypo_details
        sections["Aktuelle Symptome"] = symptome

        medikation: dict[str, str] = {}
        med_value = answers.get("medikamente", "")
        if med_value:
            medikation["Aktuelle Medikamente"] = med_value
        diag_value = answers.get("bekannte_diagnosen", "")
        if diag_value:
            medikation["Bekannte Diagnosen"] = diag_value
        sections["Medikation"] = medikation

        komplikationen: dict[str, str] = {}
        fe_bekannt = answers.get("folgeerkrankungen_bekannt", "")
        if fe_bekannt:
            komplikationen["Folgeerkrankungen bekannt"] = fe_bekannt
        fe_details = answers.get("folgeerkrankungen_details", "")
        if fe_details:
            komplikationen["Details"] = fe_details
        fuss = answers.get("offene_wunde_fussproblem", "")
        if fuss:
            komplikationen["Fussprobleme oder Wunden"] = fuss
        fuss_details = answers.get("offene_wunde_fussproblem_details", "")
        if fuss_details:
            komplikationen["Fussproblem-Details"] = fuss_details
        sections["Komplikationen"] = komplikationen

        vorbefunde: dict[str, str] = {}
        hba1c_bek = answers.get("hba1c_bekannt", "")
        if hba1c_bek:
            vorbefunde["HbA1c bekannt"] = hba1c_bek
        hba1c_w = answers.get("hba1c_wert", "")
        if hba1c_w:
            vorbefunde["HbA1c-Wert"] = hba1c_w
        bz_bek = answers.get("blutzuckerwert_bekannt", "")
        if bz_bek:
            vorbefunde["Blutzuckerwert bekannt"] = bz_bek
        bz_w = answers.get("blutzuckerwert_details", "")
        if bz_w:
            vorbefunde["Blutzuckerwert"] = bz_w
        sections["Vorbefunde"] = vorbefunde

        offene_fragen: dict[str, str] = {}
        of = answers.get("offene_fragen", "")
        if of:
            offene_fragen["Patientenfragen"] = of
        ls = answers.get("lebensstil", "")
        if ls:
            offene_fragen["Lebensstil"] = ls
        sections["Offene Fragen"] = offene_fragen

        if answers:
            sections["Anamnese"] = {k: v for k, v in answers.items() if v.strip()}

    return sections
