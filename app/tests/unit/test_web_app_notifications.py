from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.patient_import.patient_schema import PatientRecord
from app.ui.web_app import (
    BrowserSession,
    _answer_yes_no,
    _apply_symptom_chat_prefill,
    _clear_prefilled_red_flag_values_for_correction,
    _complete_successful_login,
    _dismiss_critical_warning,
    _find_duplicate_patient,
    _initialize_session_from_url,
    _parse_birth_date,
    _parse_optional_iso_birth_date,
    _parse_required_iso_birth_date,
    _reset_browser_session,
    _select_patient_for_personal_mode,
    _sync_browser_url,
)


class _GuidedSessionStub(SimpleNamespace):
    @property
    def primary_controller(self):
        return self.controller


def test_dismiss_critical_warning_closes_only_red_flag_notifications(monkeypatch) -> None:
    scripts: list[str] = []
    monkeypatch.setattr("app.ui.web_app.ui.run_javascript", scripts.append)

    _dismiss_critical_warning()

    assert len(scripts) == 1
    assert ".critical-red-flag-notification" in scripts[0]
    assert "button.click()" in scripts[0]


def test_browser_back_guard_warns_user(monkeypatch) -> None:
    scripts: list[str] = []
    monkeypatch.setattr("app.ui.web_app.ui.run_javascript", scripts.append)
    session = BrowserSession(stage="scenario")

    _sync_browser_url(session)

    assert len(scripts) == 1
    assert "popstate" in scripts[0]
    assert "Browser-Zurück-Taste ist hier deaktiviert" in scripts[0]
    assert "window.Quasar.Notify.create" in scripts[0]


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


def test_dialogue_reload_returns_to_scenario_selection_with_notice(monkeypatch) -> None:
    patient = PatientRecord(
        patient_id="P-RELOAD",
        first_name="Reload",
        last_name="Test",
        date_of_birth="1980-01-01",
    )
    monkeypatch.setattr("app.ui.web_app.PATIENTS", [patient])
    monkeypatch.setattr(
        "app.ui.web_app._request_url_state",
        lambda: {
            "page": "dialogue",
            "patient": "P-RELOAD",
            "scenarios": "B,D",
        },
    )

    session = BrowserSession()

    _initialize_session_from_url(session)

    assert session.current_patient is patient
    assert session.selected_scenarios == ["B", "D"]
    assert session.stage == "scenario"
    assert session.controllers == []
    assert session.reload_message == "Der laufende Dialog wurde neu gestartet."


def test_guided_yes_no_critical_opens_confirmation_before_callback(monkeypatch) -> None:
    callback_calls: list[str] = []
    refresh_calls: list[bool] = []

    controller = SimpleNamespace(
        current_question=SimpleNamespace(key="akut_verwirrt_bewusstlos")
    )
    callback = lambda answer: callback_calls.append(answer)
    session = _GuidedSessionStub(
        controller=controller,
        pending_input=callback,
        messages=[],
    )

    def fake_live_check(session_arg, controllers, answers, refresh_ui, vitals=None):
        assert session_arg is session
        assert controllers == [controller]
        assert answers == {"akut_verwirrt_bewusstlos": "ja"}
        assert vitals is None
        return True

    monkeypatch.setattr("app.ui.web_app._check_live_form_escalation", fake_live_check)

    _answer_yes_no(session, "ja", lambda: refresh_calls.append(True))

    assert callback_calls == []
    assert refresh_calls == []
    assert session.pending_input is callback
    assert session.messages == []


def test_symptom_chat_prefill_runs_live_escalation(monkeypatch) -> None:
    calls: list[dict] = []
    controller = SimpleNamespace()
    session = SimpleNamespace(
        prefilled_answers={},
        ai_prefilled_keys=set(),
        chat_phase_done=False,
        critical_confirmation_open=False,
    )
    prefilled = {"akut_verwirrt_bewusstlos": "ja"}

    def fake_live_check(
        session_arg,
        controllers,
        answers,
        refresh_ui,
        vitals=None,
        refresh_on_correct=False,
    ):
        calls.append(
            {
                "session": session_arg,
                "controllers": controllers,
                "answers": answers,
                "vitals": vitals,
                "refresh_on_correct": refresh_on_correct,
            }
        )
        return True

    monkeypatch.setattr("app.ui.web_app._check_live_form_escalation", fake_live_check)

    blocked = _apply_symptom_chat_prefill(
        session,
        prefilled,
        [controller],
        lambda: None,
    )

    assert blocked is True
    assert session.prefilled_answers == prefilled
    assert session.ai_prefilled_keys == set(prefilled)
    assert session.chat_phase_done is True
    assert calls == [
        {
            "session": session,
            "controllers": [controller],
            "answers": prefilled,
            "vitals": None,
            "refresh_on_correct": True,
        }
    ]


def test_correcting_prefilled_red_flag_clears_triggering_answer_only() -> None:
    session = SimpleNamespace(
        prefilled_answers={
            "akut_verwirrt_bewusstlos": "ja",
            "sehstoerungen": "nein",
        },
        ai_prefilled_keys={"akut_verwirrt_bewusstlos", "sehstoerungen"},
    )

    cleared = _clear_prefilled_red_flag_values_for_correction(
        session,
        session.prefilled_answers.copy(),
        [SimpleNamespace(triggered_by="akut_verwirrt_bewusstlos=ja")],
    )

    assert cleared == {"akut_verwirrt_bewusstlos"}
    assert session.prefilled_answers == {"sehstoerungen": "nein"}
    assert session.ai_prefilled_keys == {"sehstoerungen"}


def test_correcting_prefilled_red_flag_clears_blood_pressure_pair() -> None:
    session = SimpleNamespace(
        prefilled_answers={
            "blutdruck_systolisch": "190",
            "blutdruck_diastolisch": "90",
            "kopfschmerz": "nein",
        },
        ai_prefilled_keys={
            "blutdruck_systolisch",
            "blutdruck_diastolisch",
            "kopfschmerz",
        },
    )

    cleared = _clear_prefilled_red_flag_values_for_correction(
        session,
        session.prefilled_answers.copy(),
        [SimpleNamespace(triggered_by="systolisch=190")],
    )

    assert cleared == {"blutdruck_systolisch", "blutdruck_diastolisch"}
    assert session.prefilled_answers == {"kopfschmerz": "nein"}
    assert session.ai_prefilled_keys == {"kopfschmerz"}


def test_guided_yes_no_noncritical_continues_normally(monkeypatch) -> None:
    callback_calls: list[str] = []
    refresh_calls: list[bool] = []
    controller = SimpleNamespace(current_question=SimpleNamespace(key="sehstoerungen"))
    session = _GuidedSessionStub(
        controller=controller,
        pending_input=lambda answer: callback_calls.append(answer),
        messages=[],
    )

    monkeypatch.setattr(
        "app.ui.web_app._check_live_form_escalation",
        lambda session, controllers, answers, refresh_ui, vitals=None: False,
    )

    _answer_yes_no(session, "nein", lambda: refresh_calls.append(True))

    assert callback_calls == ["nein"]
    assert refresh_calls == [True]
    assert session.pending_input is None
    assert session.messages[-1].text == "nein"
