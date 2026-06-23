from types import SimpleNamespace

from nicegui import ui

from app.ui.web_app import (
    _SliderField,
    _set_unknown_state,
    _simulate_weight_in_form,
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
    slider = ui.slider(min=30, max=300, step=1, value=30)
    checkbox = ui.checkbox("unbekannt", value=True)
    number_input = ui.number("Messwert", value=30, min=30, max=300, step=1)
    info_label = ui.label("")
    field = _SliderField(slider, checkbox, number_input, 30, 300, 1, info_label)
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
    assert field.value == "72"
    assert field.measurement_source == "simuliert"
    assert "BMI: 25.1" in info_label.text
