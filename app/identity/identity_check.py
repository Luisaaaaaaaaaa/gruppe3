from dataclasses import dataclass

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
        normalized_first_name = first_name.strip().casefold()
        normalized_last_name = last_name.strip().casefold()
        normalized_birth_date = date_of_birth.strip()

        patient = next(
            (
                candidate
                for candidate in self._patients
                if candidate.first_name.casefold() == normalized_first_name
                and candidate.last_name.casefold() == normalized_last_name
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
                message="Identitaet erfolgreich bestaetigt.",
            )

        self._failed_attempts += 1
        attempts_left = max(self._max_attempts - self._failed_attempts, 0)
        escalate = attempts_left == 0

        if escalate:
            message = (
                "Die Identitaet konnte nach drei Versuchen nicht bestaetigt werden. "
                "Bitte wenden Sie sich an das Praxispersonal."
            )
        else:
            message = (
                "Die Angaben stimmen nicht mit der Tagesliste ueberein. "
                f"Bitte pruefen Sie Ihre Eingabe. Verbleibende Versuche: {attempts_left}."
            )

        return AuthenticationResult(
            success=False,
            patient=None,
            attempts_left=attempts_left,
            message=message,
            escalate=escalate,
        )
