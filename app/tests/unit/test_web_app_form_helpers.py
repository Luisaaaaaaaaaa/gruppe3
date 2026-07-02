from types import SimpleNamespace

from nicegui import ui

from app.ui.web_app import (
    ChatEntry,
    _BloodPressureField,
    _SliderField,
    _append_guided_answer_history,
    _clear_simulator_state_for_manual_input,
    _device_prefilled_answers,
    _device_prefilled_sources,
    _merged_anamnesis_answers,
    _split_multiline_field,
    _set_unknown_state,
    _simulate_oximeter_in_form,
    _simulate_weight_in_form,
    _update_simulator_state_from_form,
)


class _ControlStub:
    def __init__(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def enable(self) -> None:
        self.enabled = True


def test_unknown_state_can_be_reversed_for_manual_input() -> None:
    control = _ControlStub()

    _set_unknown_state(True, control)
    _set_unknown_state(False, control)

    assert control.enabled is True


def test_split_multiline_field_keeps_empty_edit_as_empty_tuple() -> None:
    assert _split_multiline_field("") == ()
    assert _split_multiline_field("  Hypertonie  \n\nDiabetes ") == (
        "Hypertonie",
        "Diabetes",
    )


def test_merged_anamnesis_answers_prefers_latest_draft_values() -> None:
    question_symptom = SimpleNamespace(key="symptom")
    question_duration = SimpleNamespace(key="duration")
    controller = SimpleNamespace(
        get_questions_with_answers=lambda: [
            (question_symptom, "controller"),
            (question_duration, "seit gestern"),
        ]
    )
    session = SimpleNamespace(
        prefilled_answers={"symptom": "ki", "temperature": "38"},
        draft_answers={"symptom": "draft"},
        simulated_bp=None,
        simulated_weight=None,
        simulated_oximeter=None,
    )

    merged = _merged_anamnesis_answers(session, [controller])

    assert merged["symptom"] == "draft"
    assert merged["duration"] == "seit gestern"
    assert merged["temperature"] == "38"


def test_guided_answer_history_adds_form_answers_once() -> None:
    question_symptom = SimpleNamespace(
        key="symptom",
        text="Welche Beschwerden haben Sie?",
    )
    question_duration = SimpleNamespace(
        key="duration",
        text="Seit wann bestehen die Beschwerden?",
    )
    controller = SimpleNamespace(
        get_questions_with_answers=lambda: [
            (question_symptom, ""),
            (question_duration, ""),
        ],
        is_question_visible=lambda key, answers: True,
    )
    session = SimpleNamespace(
        messages=[],
        guided_answer_message_keys=set(),
        guided_answer_message_values={},
        guided_answer_message_indices={},
    )

    _append_guided_answer_history(
        session,
        [controller],
        {"symptom": "Husten", "duration": "seit gestern"},
    )
    _append_guided_answer_history(
        session,
        [controller],
        {"symptom": "Husten", "duration": "seit gestern"},
    )

    assert [
        (entry.role, entry.text)
        for entry in session.messages
    ] == [
        ("system", "Welche Beschwerden haben Sie?"),
        ("user", "Husten"),
        ("system", "Seit wann bestehen die Beschwerden?"),
        ("user", "seit gestern"),
    ]
    assert session.guided_answer_message_keys == {"symptom", "duration"}
    assert session.guided_answer_message_values == {
        "symptom": "Husten",
        "duration": "seit gestern",
    }
    assert session.guided_answer_message_indices == {
        "symptom": 1,
        "duration": 3,
    }


def test_guided_answer_history_includes_later_form_answers_even_if_not_visible() -> None:
    question_first = SimpleNamespace(
        key="first",
        text="Erste Frage?",
    )
    question_later = SimpleNamespace(
        key="later",
        text="Spaetere Frage?",
    )
    controller = SimpleNamespace(
        get_questions_with_answers=lambda: [
            (question_first, ""),
            (question_later, ""),
        ],
        is_question_visible=lambda key, answers: key != "later",
    )
    session = SimpleNamespace(
        messages=[],
        guided_answer_message_keys=set(),
        guided_answer_message_values={},
        guided_answer_message_indices={},
    )

    _append_guided_answer_history(
        session,
        [controller],
        {"later": "schon beantwortet"},
    )

    assert [
        (entry.role, entry.text)
        for entry in session.messages
    ] == [
        ("system", "Spaetere Frage?"),
        ("user", "schon beantwortet"),
    ]


def test_guided_answer_history_updates_changed_form_answer_in_place() -> None:
    question = SimpleNamespace(
        key="symptom",
        text="Welche Beschwerden haben Sie?",
    )
    controller = SimpleNamespace(
        get_questions_with_answers=lambda: [(question, "")],
        is_question_visible=lambda key, answers: True,
    )
    session = SimpleNamespace(
        messages=[],
        guided_answer_message_keys=set(),
        guided_answer_message_values={},
        guided_answer_message_indices={},
    )

    _append_guided_answer_history(session, [controller], {"symptom": "Husten"})
    session.messages.append(ChatEntry(role="system", text="Naechste Frage?", tone="system"))
    _append_guided_answer_history(session, [controller], {"symptom": "Fieber"})

    assert [
        (entry.role, entry.text)
        for entry in session.messages
    ] == [
        ("system", "Welche Beschwerden haben Sie?"),
        ("user", "Fieber"),
        ("system", "Naechste Frage?"),
    ]
    assert session.guided_answer_message_indices == {"symptom": 1}


def test_guided_answer_history_inserts_later_answer_before_pending_question() -> None:
    current_question = SimpleNamespace(
        key="current",
        text="Aktuelle Frage?",
    )
    later_question = SimpleNamespace(
        key="later",
        text="Spaetere Frage?",
    )
    controller = SimpleNamespace(
        current_question=current_question,
        get_questions_with_answers=lambda: [
            (current_question, ""),
            (later_question, ""),
        ],
        is_question_visible=lambda key, answers: True,
    )
    session = SimpleNamespace(
        messages=[
            ChatEntry(role="system", text="Aktuelle Frage?", tone="system"),
        ],
        guided_answer_message_keys=set(),
        guided_answer_message_values={},
        guided_answer_message_indices={},
    )

    _append_guided_answer_history(
        session,
        [controller],
        {"later": "Antwort spaeter"},
    )

    assert [
        (entry.role, entry.text)
        for entry in session.messages
    ] == [
        ("system", "Spaetere Frage?"),
        ("user", "Antwort spaeter"),
        ("system", "Aktuelle Frage?"),
    ]
    assert session.guided_answer_message_indices == {"later": 1}


def test_guided_answer_history_answers_pending_question_in_place() -> None:
    current_question = SimpleNamespace(
        key="current",
        text="Aktuelle Frage?",
    )
    controller = SimpleNamespace(
        current_question=current_question,
        get_questions_with_answers=lambda: [(current_question, "")],
        is_question_visible=lambda key, answers: True,
    )
    session = SimpleNamespace(
        messages=[
            ChatEntry(role="system", text="Aktuelle Frage?", tone="system"),
        ],
        guided_answer_message_keys=set(),
        guided_answer_message_values={},
        guided_answer_message_indices={},
    )

    _append_guided_answer_history(
        session,
        [controller],
        {"current": "Antwort aktuell"},
    )

    assert [
        (entry.role, entry.text)
        for entry in session.messages
    ] == [
        ("system", "Aktuelle Frage?"),
        ("user", "Antwort aktuell"),
    ]
    assert session.guided_answer_message_indices == {"current": 1}


def test_unknown_state_updates_all_blood_pressure_controls() -> None:
    systolic = _ControlStub()
    diastolic = _ControlStub()

    _set_unknown_state(True, systolic, diastolic)
    assert not systolic.enabled
    assert not diastolic.enabled

    _set_unknown_state(False, systolic, diastolic)
    assert systolic.enabled
    assert diastolic.enabled


def test_slider_field_without_recorded_value_stays_empty() -> None:
    slider = ui.slider(min=0, max=10, step=1, value=0)
    checkbox = ui.checkbox("unbekannt", value=False)
    number_input = ui.number("Messwert", value=0, min=0, max=10, step=1)
    field = _SliderField(slider, checkbox, number_input, 0, 10, 1)

    assert field.value == ""

    field.value_recorded = True

    assert field.value == "0"


def test_blood_pressure_field_without_recorded_value_stays_empty() -> None:
    sys_slider = ui.slider(min=80, max=250, step=1, value=120)
    sys_input = ui.number("Oberer Wert", value=120, min=80, max=250, step=1)
    dia_slider = ui.slider(min=40, max=150, step=1, value=80)
    dia_input = ui.number("Unterer Wert", value=80, min=40, max=150, step=1)
    checkbox = ui.checkbox("unbekannt", value=False)
    field = _BloodPressureField(
        sys_slider, sys_input, dia_slider, dia_input, checkbox
    )

    assert field.value == ""
    assert field.sys_value == ""
    assert field.dia_value == ""

    checkbox.set_value(True)

    assert field.value == "unbekannt"
    assert field.sys_value == "unbekannt"
    assert field.dia_value == "unbekannt"


def test_weight_simulator_recovers_from_unknown_state(monkeypatch) -> None:
    slider = ui.slider(min=30, max=300, step=0.1, value=30)
    checkbox = ui.checkbox("unbekannt", value=True)
    number_input = ui.number("Messwert", value=30, min=30, max=300, step=0.1)
    info_label = ui.label("")
    field = _SliderField(slider, checkbox, number_input, 30, 300, 0.1, info_label)
    slider.disable()
    number_input.disable()

    patient = SimpleNamespace(
        details=SimpleNamespace(gender="weiblich", groesse_cm=170),
        date_of_birth="1990-01-01",
    )
    controller = SimpleNamespace(get_patient=lambda: patient)
    monkeypatch.setattr(
        "app.ui.web_app.Simulator.gewicht",
        lambda _: {"gewicht": 72.5, "bmi": 25.1, "klasse": "Normalgewicht"},
    )

    _simulate_weight_in_form({"gewicht_aktuell": field}, controller)

    assert checkbox.value is False
    assert slider.enabled is True
    assert number_input.enabled is True
    assert slider.value == 72.5
    assert number_input.value == 72.5
    assert field.value == "72.5"
    assert field.measurement_source == "simuliert"
    assert "BMI: 25.1" in info_label.text


def test_oximeter_simulator_sets_spo2_and_pulse(monkeypatch) -> None:
    spo2_slider = ui.slider(min=70, max=100, step=1, value=70)
    spo2_checkbox = ui.checkbox("unbekannt", value=True)
    spo2_input = ui.number("Messwert", value=70, min=70, max=100, step=1)
    spo2_field = _SliderField(spo2_slider, spo2_checkbox, spo2_input, 70, 100, 1)
    spo2_slider.disable()
    spo2_input.disable()

    pulse_slider = ui.slider(min=30, max=250, step=1, value=30)
    pulse_checkbox = ui.checkbox("unbekannt", value=True)
    pulse_input = ui.number("Messwert", value=30, min=30, max=250, step=1)
    pulse_field = _SliderField(pulse_slider, pulse_checkbox, pulse_input, 30, 250, 1)

    patient = SimpleNamespace(
        details=SimpleNamespace(gender="weiblich", groesse_cm=170),
        date_of_birth="1990-01-01",
    )
    controller = SimpleNamespace(get_patient=lambda: patient)
    monkeypatch.setattr(
        "app.ui.web_app.Simulator.pulsoximeter",
        lambda _: {"spo2": 94, "puls": 88},
    )

    result = _simulate_oximeter_in_form(
        {"spo2": spo2_field, "puls": pulse_field}, controller
    )

    assert result == {"spo2": 94, "puls": 88}
    assert spo2_checkbox.value is False
    assert spo2_slider.enabled is True
    assert spo2_input.enabled is True
    assert spo2_field.value == "94"
    assert spo2_field.measurement_source == "simuliert"
    assert pulse_field.value == "88"
    assert pulse_field.measurement_source == "simuliert"


def test_device_prefill_maps_sidebar_simulator_values_to_anamnesis_fields() -> None:
    session = SimpleNamespace(
        simulated_bp={"systolisch": 131, "diastolisch": 76},
        simulated_weight={"gewicht": 67.0},
        simulated_oximeter={"spo2": 98, "puls": 78},
    )

    assert _device_prefilled_answers(session) == {
        "blutdruck_systolisch": "131",
        "blutdruck_diastolisch": "76",
        "gewicht": "67.0",
        "gewicht_aktuell": "67.0",
        "spo2": "98",
        "puls": "78",
    }
    assert _device_prefilled_sources(session) == {
        "systolisch": "simuliert",
        "diastolisch": "simuliert",
        "gewicht": "simuliert",
        "spo2": "simuliert",
        "puls": "simuliert",
    }


def test_form_simulator_updates_sidebar_state_and_controller_vitals() -> None:
    recorded: list[tuple[dict, str]] = []
    controller = SimpleNamespace(record_vitals=lambda values, source: recorded.append((values, source)))
    session = SimpleNamespace(
        simulated_bp=None,
        simulated_weight=None,
        simulated_oximeter=None,
        controllers=[controller],
        controller=None,
    )

    _update_simulator_state_from_form(
        session, "blood_pressure", {"systolisch": 140, "diastolisch": 90}
    )
    _update_simulator_state_from_form(
        session, "weight", {"gewicht": 72.5, "bmi": 25.1, "klasse": "Normalgewicht"}
    )
    _update_simulator_state_from_form(session, "pulse", {"puls": 82})
    _update_simulator_state_from_form(session, "oximeter", {"spo2": 94, "puls": 88})

    assert session.simulated_bp == {"systolisch": 140, "diastolisch": 90}
    assert session.simulated_weight["gewicht"] == 72.5
    assert session.simulated_oximeter == {"spo2": 94, "puls": 88}
    assert ({"systolisch": 140, "diastolisch": 90}, "simuliert") in recorded
    assert ({"gewicht": 72.5}, "simuliert") in recorded
    assert ({"puls": 82}, "simuliert") in recorded
    assert ({"spo2": 94, "puls": 88}, "simuliert") in recorded


def test_manual_vital_input_clears_matching_sidebar_simulator_state() -> None:
    recorded: list[tuple[dict, str]] = []
    cleared: list[tuple[str, ...]] = []
    controller = SimpleNamespace(
        record_vitals=lambda values, source: recorded.append((values, source)),
        clear_vitals=lambda keys: cleared.append(tuple(keys)),
    )
    session = SimpleNamespace(
        simulated_bp={"systolisch": 131, "diastolisch": 76},
        simulated_weight={"gewicht": 67.0, "bmi": 23.2, "klasse": "Normalgewicht"},
        simulated_oximeter={"spo2": 98, "puls": 78},
        prefilled_answers={},
        controllers=[controller],
        controller=None,
    )

    _clear_simulator_state_for_manual_input(
        session,
        "blood_pressure",
        {"blutdruck_systolisch": "145", "blutdruck_diastolisch": "91"},
    )
    _clear_simulator_state_for_manual_input(
        session,
        "weight",
        {"gewicht_aktuell": "70"},
    )
    _clear_simulator_state_for_manual_input(
        session,
        "pulse",
        {"puls": "82"},
    )
    session.simulated_oximeter = {"spo2": 98, "puls": 78}
    _clear_simulator_state_for_manual_input(
        session,
        "oximeter",
        {"spo2": "96"},
    )

    assert session.simulated_bp is None
    assert session.simulated_weight is None
    assert session.simulated_oximeter is None
    assert session.prefilled_answers["blutdruck_systolisch"] == "145"
    assert session.prefilled_answers["gewicht_aktuell"] == "70"
    assert session.prefilled_answers["puls"] == "82"
    assert session.prefilled_answers["spo2"] == "96"
    assert ({"systolisch": 145.0, "diastolisch": 91.0}, "manuell eingegeben") in recorded
    assert ({"gewicht": 70.0}, "manuell eingegeben") in recorded
    assert ({"puls": 82.0}, "manuell eingegeben") in recorded
    assert ({"spo2": 96.0}, "manuell eingegeben") in recorded
    assert cleared == []


def test_unknown_manual_vital_input_removes_previous_controller_value() -> None:
    recorded: list[tuple[dict, str]] = []
    cleared: list[tuple[str, ...]] = []
    controller = SimpleNamespace(
        record_vitals=lambda values, source: recorded.append((values, source)),
        clear_vitals=lambda keys: cleared.append(tuple(keys)),
    )
    session = SimpleNamespace(
        simulated_bp={"systolisch": 131, "diastolisch": 76},
        simulated_weight=None,
        simulated_oximeter=None,
        prefilled_answers={},
        controllers=[controller],
        controller=None,
    )

    _clear_simulator_state_for_manual_input(
        session,
        "blood_pressure",
        {"blutdruck_systolisch": "unbekannt", "blutdruck_diastolisch": "unbekannt"},
    )

    assert session.simulated_bp is None
    assert recorded == []
    assert cleared == [("systolisch", "diastolisch")]
