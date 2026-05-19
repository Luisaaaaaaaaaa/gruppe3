from dataclasses import dataclass


@dataclass(frozen=True)
class PatientRecord:
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
