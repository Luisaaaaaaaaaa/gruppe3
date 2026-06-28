from app.dialogue.dialogue_controller import DialogueController
from app.patient_import.patient_schema import PatientRecord


def _make_patient() -> PatientRecord:
    return PatientRecord(
        patient_id="P-COUGH-001",
        first_name="Test",
        last_name="Person",
        date_of_birth="1970-01-01",
    )


def _controller() -> DialogueController:
    return DialogueController(
        scenario_key="A",
        patient=_make_patient(),
        display_message=lambda _: None,
        request_input=lambda _: None,
    )


def test_cough_follow_ups_are_conditional() -> None:
    controller = _controller()

    assert not controller.is_question_visible("auswurf_farbe", {"auswurf": "nein"})
    assert controller.is_question_visible("auswurf_farbe", {"auswurf": "ja"})
    assert not controller.is_question_visible("ruhedyspnoe", {"dyspnoe": "nein"})
    assert controller.is_question_visible("ruhedyspnoe", {"dyspnoe": "ja"})
    assert not controller.is_question_visible(
        "atemabhaengige_schmerzen", {"thorakale_schmerzen": "nein"}
    )
    assert not controller.is_question_visible("spo2", {"dyspnoe": "nein"})
    assert controller.is_question_visible("spo2", {"dyspnoe": "ja"})
    assert controller.is_question_visible("spo2", {"zyanose": "ja"})
    assert controller.is_question_visible("spo2", {"chronische_lungenerkrankung": "ja"})


def test_general_shortness_of_breath_keeps_follow_up_questions_available() -> None:
    controller = _controller()
    controller._answers = {"dyspnoe": "ja"}

    assert controller._escalate_critical_cough_answers() is False
    assert controller.is_question_visible("ruhedyspnoe", controller._answers)
    assert controller.is_question_visible("sprechen_beeintraechtigt", controller._answers)


def test_routine_cough_does_not_simulate_unrelated_vitals() -> None:
    controller = _controller()
    controller._answers = {
        "fieber": "nein",
        "belastungsdyspnoe": "nein",
        "reduzierter_allgemeinzustand": "nein",
        "thorakale_schmerzen": "nein",
        "chronische_lungenerkrankung": "nein",
        "atemfrequenz": "nicht gemessen",
    }

    controller._measure_cough_vitals()

    assert controller._vitals == {}
    assert controller._vitals_source == "nicht erhoben"


def test_indication_does_not_silently_start_pulse_oximeter() -> None:
    controller = _controller()
    controller._answers = {
        "belastungsdyspnoe": "ja",
        "korpertemperatur": "38,2 °C",
    }

    controller._measure_cough_vitals()

    assert controller._vitals == {"temperatur": 38.2}
    assert controller._vital_sources == {"temperatur": "manuell eingegeben"}


def test_explicit_simulator_values_keep_per_value_sources() -> None:
    controller = _controller()
    controller._answers = {"korpertemperatur": "38,2 °C"}
    controller.record_vitals({"spo2": 97, "puls": 78}, "simuliert")

    controller._measure_cough_vitals()

    assert controller._vitals == {"temperatur": 38.2, "spo2": 97, "puls": 78}
    assert controller._vital_sources == {
        "spo2": "simuliert",
        "puls": "simuliert",
        "temperatur": "manuell eingegeben",
    }
    assert controller._vitals_source == "simuliert, manuell eingegeben"
