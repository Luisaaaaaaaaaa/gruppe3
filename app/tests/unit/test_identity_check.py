from app.identity.identity_check import IdentityCheck
from app.patient_import.patient_schema import PatientRecord


def test_authentication_succeeds_with_matching_patient() -> None:
    service = IdentityCheck(
        [
            PatientRecord(
                patient_id="P1",
                first_name="Laura",
                last_name="Schneider",
                date_of_birth="1986-03-14",
            )
        ]
    )

    result = service.authenticate("Laura", "Schneider", "1986-03-14")

    assert result.success is True
    assert result.patient is not None
    assert result.patient.patient_id == "P1"


def test_authentication_normalizes_name_spacing_and_hyphens() -> None:
    service = IdentityCheck(
        [
            PatientRecord(
                patient_id="P1",
                first_name="Anne-Marie",
                last_name="Muster Schmidt",
                date_of_birth="1986-03-14",
            )
        ]
    )

    result = service.authenticate(
        "  Anne  -  Marie ",
        "Muster   Schmidt",
        "1986-03-14",
    )

    assert result.success is True
    assert result.patient is not None
    assert result.patient.patient_id == "P1"


def test_authentication_escalates_after_three_failures() -> None:
    service = IdentityCheck(
        [
            PatientRecord(
                patient_id="P1",
                first_name="Laura",
                last_name="Schneider",
                date_of_birth="1986-03-14",
            )
        ],
        max_attempts=3,
    )

    service.authenticate("A", "B", "2000-01-01")
    service.authenticate("A", "B", "2000-01-01")
    result = service.authenticate("A", "B", "2000-01-01")

    assert result.success is False
    assert result.escalate is True
    assert result.attempts_left == 0
