from app.dialogue.dialogue_controller import DialogueController
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

