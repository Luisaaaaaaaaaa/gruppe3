from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.patient_import.patient_schema import PatientRecord
from app.ui.web_app import (
    _complete_successful_login,
    _dismiss_critical_warning,
    _find_duplicate_patient,
    _parse_birth_date,
    _parse_optional_iso_birth_date,
    _parse_required_iso_birth_date,
    _reset_browser_session,
    _select_patient_for_personal_mode,
)


def test_dismiss_critical_warning_closes_only_red_flag_notifications(monkeypatch) -> None:
    scripts: list[str] = []
    monkeypatch.setattr("app.ui.web_app.ui.run_javascript", scripts.append)

    _dismiss_critical_warning()

    assert len(scripts) == 1
    assert ".critical-red-flag-notification" in scripts[0]
    assert "button.click()" in scripts[0]


def test_selecting_another_patient_dismisses_previous_warning(monkeypatch) -> None:
    dismissed: list[bool] = []
    monkeypatch.setattr(
        "app.ui.web_app._dismiss_critical_warning", lambda: dismissed.append(True)
    )
    monkeypatch.setattr(
        "app.ui.web_app._get_recommended_scenario_ui_key", lambda _: None
    )
    session = SimpleNamespace(
        current_patient=SimpleNamespace(patient_id="P-1"),
        selected_scenarios=[],
        login_message="old",
        login_tone="tone-danger",
    )
    patient = SimpleNamespace(patient_id="P-2")

    _select_patient_for_personal_mode(session, patient, lambda: None)

    assert dismissed == [True]
    assert session.current_patient is patient


def test_select_patient_uses_saved_prepared_scenarios(monkeypatch) -> None:
    monkeypatch.setattr("app.ui.web_app._dismiss_critical_warning", lambda: None)
    monkeypatch.setattr(
        "app.ui.web_app._get_recommended_scenario_ui_key", lambda _: "A"
    )
    session = SimpleNamespace(
        current_patient=None,
        selected_scenarios=[],
        login_message="old",
        login_tone="tone-danger",
    )
    patient = PatientRecord(
        patient_id="P-1",
        prepared_scenarios=("B", "D"),
        prepared_scenarios_saved=True,
    )

    _select_patient_for_personal_mode(session, patient, lambda: None)

    assert session.selected_scenarios == ["B", "D"]


def test_reset_browser_session_dismisses_warning_before_reset(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.ui.web_app._dismiss_critical_warning", lambda: calls.append("dismiss")
    )
    session = SimpleNamespace(reset=lambda: calls.append("reset"))

    _reset_browser_session(session, lambda: calls.append("refresh"))

    assert calls == ["dismiss", "reset", "refresh"]


def test_patient_login_rejects_future_birth_date() -> None:
    future = date.today() + timedelta(days=1)

    with pytest.raises(ValueError, match="Zukunft"):
        _parse_birth_date(str(future.day), str(future.month), str(future.year))


def test_personal_form_rejects_future_birth_date() -> None:
    future = date.today() + timedelta(days=1)

    with pytest.raises(ValueError, match="Zukunft"):
        _parse_optional_iso_birth_date(future.isoformat())


def test_personal_form_allows_empty_birth_date() -> None:
    assert _parse_optional_iso_birth_date("") == ""


def test_required_birth_date_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="Geburtsdatum"):
        _parse_required_iso_birth_date("")


def test_duplicate_patient_check_normalizes_names(monkeypatch) -> None:
    existing = PatientRecord(
        patient_id="P1",
        first_name="Anne-Marie",
        last_name="Muster Schmidt",
        date_of_birth="1986-03-14",
    )
    monkeypatch.setattr("app.ui.web_app.PATIENTS", [existing])

    duplicate = _find_duplicate_patient(
        " Anne - Marie ",
        "Muster   Schmidt",
        "1986-03-14",
    )

    assert duplicate is existing


def test_duplicate_patient_check_ignores_current_patient(monkeypatch) -> None:
    existing = PatientRecord(
        patient_id="P1",
        first_name="Anne-Marie",
        last_name="Muster Schmidt",
        date_of_birth="1986-03-14",
    )
    monkeypatch.setattr("app.ui.web_app.PATIENTS", [existing])

    duplicate = _find_duplicate_patient(
        "Anne-Marie",
        "Muster Schmidt",
        "1986-03-14",
        exclude_patient_id="P1",
    )

    assert duplicate is None


def test_successful_login_sets_patient_and_resets_state(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.ui.web_app._dismiss_critical_warning", lambda: calls.append("dismiss")
    )
    session = SimpleNamespace(
        current_patient=None,
        attempts_left=0,
        login_message="old",
        login_tone="tone-danger",
        login_blocked_until=123.0,
        identity_check=None,
        is_personal_mode=False,
        selected_scenarios=[],
        stage="login",
    )
    patient = SimpleNamespace(patient_id="PRA-0004711")

    _complete_successful_login(session, patient, lambda: calls.append("refresh"))

    assert calls == ["dismiss", "refresh"]
    assert session.current_patient is patient
    assert session.attempts_left == 3
    assert session.login_message == ""
    assert session.login_tone == "tone-info"
    assert session.login_blocked_until is None
    assert session.stage == "scenario"
