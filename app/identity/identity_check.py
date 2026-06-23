from dataclasses import dataclass

from app.identity.name_normalization import person_name_key
from app.patient_import.patient_schema import PatientRecord


@dataclass(frozen=True)
class AuthenticationResult:
    success: bool
    patient: PatientRecord | None
    attempts_left: int
    message: str
    escalate: bool = False


class IdentityCheck:
    def __init__(self, patients: list[PatientRecord], max_attempts: int = 3) -> None:
        self._patients = patients
        self._max_attempts = max_attempts
        self._failed_attempts = 0

    @property
    def patients(self) -> list[PatientRecord]:
        return self._patients

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    def authenticate(
        self, first_name: str, last_name: str, date_of_birth: str
    ) -> AuthenticationResult:
        normalized_first_name = person_name_key(first_name)
        normalized_last_name = person_name_key(last_name)
        normalized_birth_date = date_of_birth.strip()

        patient = next(
            (
                candidate
                for candidate in self._patients
                if person_name_key(candidate.first_name) == normalized_first_name
                and person_name_key(candidate.last_name) == normalized_last_name
                and candidate.date_of_birth == normalized_birth_date
            ),
            None,
        )

        if patient is not None:
            self._failed_attempts = 0
            return AuthenticationResult(
                success=True,
                patient=patient,
                attempts_left=self._max_attempts,
                message="Identität erfolgreich bestätigt.",
            )

        self._failed_attempts += 1
        attempts_left = max(self._max_attempts - self._failed_attempts, 0)
        escalate = attempts_left == 0

        if escalate:
            message = (
                "Die Identität konnte nach drei Versuchen nicht bestätigt werden. "
                "Bitte wenden Sie sich an das Praxispersonal."
            )
        else:
            message = (
                "Die Angaben stimmen nicht mit der Tagesliste überein. "
                f"Bitte prüfen Sie Ihre Eingabe. Verbleibende Versuche: {attempts_left}."
            )

        return AuthenticationResult(
            success=False,
            patient=None,
            attempts_left=attempts_left,
            message=message,
            escalate=escalate,
        )
