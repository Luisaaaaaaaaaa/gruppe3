from types import SimpleNamespace

from nicegui import ui

from app.ui.web_app import (
    _SliderField,
    _clear_simulator_state_for_manual_input,
    _device_prefilled_answers,
    _device_prefilled_sources,
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


def test_unknown_state_updates_all_blood_pressure_controls() -> None:
    systolic = _ControlStub()
    diastolic = _ControlStub()

    _set_unknown_state(True, systolic, diastolic)
    assert not systolic.enabled
    assert not diastolic.enabled

    _set_unknown_state(False, systolic, diastolic)
    assert systolic.enabled
    assert diastolic.enabled


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
