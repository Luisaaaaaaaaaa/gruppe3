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
    )
