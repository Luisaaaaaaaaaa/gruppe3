from app.dialogue.dialogue_controller import DialogueController
from app.dialogue.state_machine import DialogueState
from app.patient_import.patient_schema import PatientRecord
from app.scenarios.hypertension_scenario import QUESTIONS


def _patient(*, medications: list[str] | None = None) -> PatientRecord:
    return PatientRecord(
        patient_id="HYP-TEST-1",
        first_name="Test",
        last_name="Patient",
        date_of_birth="1970-01-01",
        medications=medications or [],
    )


def _controller(*, medications: list[str] | None = None) -> DialogueController:
    return DialogueController(
        scenario_key="C",
        patient=_patient(medications=medications),
        display_message=lambda _text: None,
        request_input=lambda _callback: None,
    )


def test_patient_questions_avoid_medical_jargon() -> None:
    jargon = (
        "hypertonie",
        "systolisch",
        "diastolisch",
        "neurologisch",
        "dyspnoe",
        "synkope",
        "adhärenz",
    )
    question_text = " ".join(question.text.lower() for question in QUESTIONS)

    assert not any(term in question_text for term in jargon)


def test_known_hypertension_shows_control_branch_only() -> None:
    controller = _controller()
    answers = {"bluthochdruck_bekannt": "ja", "heimwerte_vorhanden": "ja"}

    assert controller.is_question_visible("letzte_kontrolle", answers)
    assert controller.is_question_visible("heimwerte_verlauf", answers)
    assert not controller.is_question_visible("auffaelliger_wert_wann", answers)


def test_first_abnormal_value_shows_initial_branch_only() -> None:
    controller = _controller()
    answers = {"bluthochdruck_bekannt": "nein"}

    assert controller.is_question_visible("auffaelliger_wert_wann", answers)
    assert controller.is_question_visible("mehrfach_gemessen", answers)
    assert not controller.is_question_visible("letzte_kontrolle", answers)


def test_home_value_details_only_follow_positive_answer() -> None:
    controller = _controller()

    assert not controller.is_question_visible(
        "heimwerte_verlauf",
        {"bluthochdruck_bekannt": "ja", "heimwerte_vorhanden": "nein"},
    )


def test_recorded_medication_adds_adherence_and_other_medication_questions() -> None:
    controller = _controller(medications=["Ramipril 5 mg"])
    keys = [question.key for question, _answer in controller.get_questions_with_answers()]

    assert "med_adhaerenz_0" in keys
    assert "weitere_medikamente" in keys


def test_critical_hypertension_answer_interrupts_immediately() -> None:
    messages: list[str] = []
    callbacks: list = []
    controller = DialogueController(
        scenario_key="C",
        patient=_patient(),
        display_message=messages.append,
        request_input=callbacks.append,
    )

    controller.start()
    callbacks.pop()("ja")
    callbacks.pop()("ja")  # Bluthochdruck bekannt
    callbacks.pop()("vor 6 Monaten")
    callbacks.pop()("nein")
    callbacks.pop()("nein")
    callbacks.pop()("190")  # oberer Blutdruckwert

    assert controller.state == DialogueState.END
    assert controller.summary is not None
    assert controller.summary.escalation_required is True
    assert "nicht als Routinefall fortgesetzt" in " ".join(messages)
