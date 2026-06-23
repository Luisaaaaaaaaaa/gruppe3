from types import SimpleNamespace

from app.ui.web_app import (
    _dismiss_critical_warning,
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


def test_reset_browser_session_dismisses_warning_before_reset(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.ui.web_app._dismiss_critical_warning", lambda: calls.append("dismiss")
    )
    session = SimpleNamespace(reset=lambda: calls.append("reset"))

    _reset_browser_session(session, lambda: calls.append("refresh"))

    assert calls == ["dismiss", "reset", "refresh"]
