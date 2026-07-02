from app.dialogue.dialogue_controller import DialogueController
from app.dialogue.state_machine import DialogueState
from app.patient_import.patient_schema import PatientDetails, PatientRecord
from app.scenarios.hypertension_scenario import QUESTIONS


def _patient(
    *,
    medications: list[str] | None = None,
    details: PatientDetails | None = None,
) -> PatientRecord:
    return PatientRecord(
        patient_id="HYP-TEST-1",
        first_name="Test",
        last_name="Patient",
        date_of_birth="1970-01-01",
        medications=medications or [],
        details=details or PatientDetails(),
    )


def _controller(
    *,
    medications: list[str] | None = None,
    details: PatientDetails | None = None,
) -> DialogueController:
    return DialogueController(
        scenario_key="C",
        patient=_patient(medications=medications, details=details),
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


def test_recorded_medication_distinguishes_daily_and_as_needed_questions() -> None:
    controller = _controller(
        medications=["Ramipril", "Ibuprofen"],
        details=PatientDetails(
            medication_details=(
                "Dauer: Ramipril 5 mg Tabletten - 1-0-0",
                "Bedarf: Ibuprofen 400 mg - bei Bedarf max. 3x täglich",
            )
        ),
    )
    keys = [question.key for question, _answer in controller.get_questions_with_answers()]

    assert "med_dauer_einnahme_0" in keys
    assert "med_dauer_aenderung_0" in keys
    assert "med_bedarf_einnahme_1" in keys
    assert "med_bedarf_grund_1" in keys
    assert "weitere_medikamente_vorhanden" in keys
    assert "weitere_medikamente" in keys


def test_medication_follow_ups_depend_on_yes_no_answers() -> None:
    controller = _controller(medications=["Ramipril", "Ibuprofen"])

    assert controller.is_question_visible(
        "med_dauer_aenderung_0", {"med_dauer_einnahme_0": "nein"}
    )
    assert not controller.is_question_visible(
        "med_dauer_aenderung_0", {"med_dauer_einnahme_0": "ja"}
    )
    assert controller.is_question_visible(
        "med_bedarf_grund_1", {"med_bedarf_einnahme_1": "ja"}
    )
    assert not controller.is_question_visible(
        "med_bedarf_grund_1", {"med_bedarf_einnahme_1": "nein"}
    )
    assert controller.is_question_visible(
        "weitere_medikamente", {"weitere_medikamente_vorhanden": "ja"}
    )
    assert not controller.is_question_visible(
        "weitere_medikamente", {"weitere_medikamente_vorhanden": "nein"}
    )


def test_hypertension_replaces_known_conditions_question_with_file_diagnoses() -> None:
    controller = _controller(
        details=PatientDetails(long_term_diagnoses=("Essentielle Hypertonie (I10)",))
    )
    keys = [question.key for question, _answer in controller.get_questions_with_answers()]

    assert "vorerkrankungen_liste" in keys
    assert "vorerkrankungen" not in keys


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
