from dataclasses import dataclass, field


@dataclass(frozen=True)
class PatientDetails:
    status: str = ""
    gender: str = ""
    language: str = ""
    contact_city: str = ""
    insurance: str = ""
    next_appointment_at: str = ""
    next_appointment_type: str = ""
    next_appointment_note: str = ""
    allergies: tuple[str, ...] = ()
    long_term_diagnoses: tuple[str, ...] = ()
    acute_diagnoses: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    medication_details: tuple[str, ...] = ()
    patient_notes: tuple[str, ...] = ()
    open_tasks: tuple[str, ...] = ()


@dataclass(frozen=True)
class PatientRecord:
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    medications: list[str] = field(default_factory=list)
    conditions: str = ""
    details: PatientDetails = field(default_factory=PatientDetails)
