import pytest

from app.dialogue.dialogue_controller import DialogueController
from app.dialogue.state_machine import DialogueState
from app.patient_import.patient_schema import PatientRecord


def test_question_progress_counts_only_displayed_questions() -> None:
    callbacks: list = []

    controller = DialogueController(
        scenario_key="D",
        patient=PatientRecord(
            patient_id="demo-1",
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
        ),
        display_message=lambda _text: None,
        request_input=lambda callback: callbacks.append(callback),
    )

    controller.start()
    callbacks.pop()("ja")

    current_question, total_questions = controller.question_progress

    assert current_question == 1
    assert total_questions == 14


@pytest.mark.parametrize(
    ("scenario_key", "critical_answers"),
    [
        ("A", {"blutbeimengung": "ja"}),
        ("B", {"ausstrahlung": "linker Arm"}),
        ("C", {"ohnmacht": "ja"}),
        ("D", {"hypo_hyper_beschwerden": "bewusstlos"}),
    ],
)
def test_partial_form_answers_escalate_immediately_for_every_scenario(
    scenario_key: str,
    critical_answers: dict[str, str],
) -> None:
    callbacks: list = []
    messages: list[str] = []
    controller = DialogueController(
        scenario_key=scenario_key,
        patient=PatientRecord(
            patient_id="live-check",
            first_name="Test",
            last_name="Patient",
            date_of_birth="1990-01-01",
        ),
        display_message=messages.append,
        request_input=callbacks.append,
    )

    controller.start()
    callbacks.pop()("ja")

    escalated = controller.check_partial_answers_for_escalation(critical_answers)

    assert escalated is True
    assert controller.state == DialogueState.END
    assert controller.summary is not None
    assert controller.summary.escalation_required is True
    assert "nicht als Routinefall fortgesetzt" in " ".join(messages)


def test_partial_device_values_escalate_before_form_submission() -> None:
    callbacks: list = []
    controller = DialogueController(
        scenario_key="C",
        patient=PatientRecord(patient_id="device-check", date_of_birth="1990-01-01"),
        display_message=lambda _text: None,
        request_input=callbacks.append,
    )
    controller.start()
    callbacks.pop()("ja")

    escalated = controller.check_partial_answers_for_escalation(
        {}, {"systolisch": 190, "diastolisch": 100}
    )

    assert escalated is True
    assert controller.state == DialogueState.END
