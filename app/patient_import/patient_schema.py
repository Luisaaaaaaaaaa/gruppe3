from dataclasses import dataclass, field


@dataclass(frozen=True)
class PatientRecord:
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    medications: list[str] = field(default_factory=list)
    conditions: str = ""
