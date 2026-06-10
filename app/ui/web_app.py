from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

try:
    from nicegui import ui
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "NiceGUI ist nicht installiert. Bitte zuerst 'pip install -r requirements.txt' ausfuehren."
    ) from exc

from app.dialogue.consent_flow import (
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_QUESTION,
    ROLE_EXPLANATION,
)
from app.dialogue.dialogue_controller import DialogueController
from app.dialogue.state_machine import DialogueState
from app.identity.identity_check import IdentityCheck
from app.patient_import.patient_list_client import PatientListClient
from app.patient_import.patient_schema import PatientRecord

MAX_ATTEMPTS = 3
PAGE_TITLE = "SET Patientenanmeldung"
STYLE_BLOCK = """
<style>
    :root {
        --app-ink: #17342f;
        --app-muted: #60716d;
        --app-panel: rgba(255, 252, 247, 0.92);
        --app-panel-strong: #fffaf2;
        --app-accent: #0f766e;
        --app-accent-soft: #d6efe9;
        --app-warning: #b55a07;
        --app-warning-soft: #fff0db;
        --app-danger: #9f1d20;
        --app-danger-soft: #fde8e8;
        --app-success: #17603d;
        --app-success-soft: #e3f5e9;
        --app-border: rgba(23, 52, 47, 0.08);
    }

    body {
        background:
            radial-gradient(circle at top left, rgba(214, 239, 233, 0.95), transparent 32%),
            radial-gradient(circle at top right, rgba(255, 228, 196, 0.65), transparent 28%),
            linear-gradient(180deg, #f6efe4 0%, #f1f6f2 58%, #edf5f3 100%);
        color: var(--app-ink);
        font-family: "Aptos", "Segoe UI", "Candara", sans-serif;
    }

    .app-shell {
        width: 100%;
        max-width: 1240px;
        margin: 0 auto;
        padding: 28px 20px 40px;
    }

    .surface-card {
        background: var(--app-panel);
        border: 1px solid var(--app-border);
        border-radius: 26px;
        box-shadow: 0 22px 55px rgba(30, 65, 60, 0.08);
        backdrop-filter: blur(10px);
    }

    .surface-card--strong {
        background: var(--app-panel-strong);
    }

    .hero-title {
        font-family: "Georgia", "Times New Roman", serif;
        letter-spacing: 0.01em;
    }

    .eyebrow {
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--app-muted);
        font-size: 0.72rem;
        font-weight: 700;
    }

    .status-chip {
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .status-chip--todo {
        background: rgba(96, 113, 109, 0.12);
        color: var(--app-muted);
    }

    .status-chip--active {
        background: var(--app-accent-soft);
        color: var(--app-accent);
    }

    .status-chip--done {
        background: var(--app-success-soft);
        color: var(--app-success);
    }

    .tone-info {
        background: rgba(15, 118, 110, 0.08);
        color: var(--app-accent);
    }

    .tone-warning {
        background: var(--app-warning-soft);
        color: var(--app-warning);
    }

    .tone-danger {
        background: var(--app-danger-soft);
        color: var(--app-danger);
    }

    .tone-success {
        background: var(--app-success-soft);
        color: var(--app-success);
    }

    .chat-shell {
        min-height: 420px;
        max-height: 62vh;
    }

    .chat-bubble {
        border-radius: 22px;
        padding: 14px 16px;
        max-width: min(88%, 760px);
        white-space: pre-wrap;
        line-height: 1.5;
    }

    .chat-bubble--system {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(23, 52, 47, 0.08);
    }

    .chat-bubble--user {
        background: linear-gradient(135deg, #0f766e 0%, #1f8a7f 100%);
        color: white;
    }

    .chat-bubble--warning {
        background: var(--app-warning-soft);
        border: 1px solid rgba(181, 90, 7, 0.2);
    }

    .chat-bubble--danger {
        background: var(--app-danger-soft);
        border: 1px solid rgba(159, 29, 32, 0.2);
    }

    .chat-bubble--success {
        background: var(--app-success-soft);
        border: 1px solid rgba(23, 96, 61, 0.2);
    }

    .scenario-card {
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    .scenario-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 40px rgba(31, 61, 58, 0.12);
    }

    .summary-label {
        color: var(--app-muted);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }

    .summary-value {
        color: var(--app-ink);
        font-size: 0.98rem;
        line-height: 1.45;
    }

    @keyframes pulse-avatar {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.08); }
    }

    .avatar-bounce {
        animation: pulse-avatar 2s ease-in-out infinite;
        transition: transform 0.2s ease;
    }
    .avatar-bounce:active {
        transform: scale(1.3) !important;
        animation: none;
    }

    @media (max-width: 767px) {
        .avatar-container { display: none !important; }
    }
</style>
"""

SCENARIOS = [
    {
        "key": "A",
        "title": "Akuter Husten",
        "subtitle": "Atemwegsinfekt oder Verdacht auf Pneumonie",
        "description": "Symptomdauer, Atemnot, Fieber, Auswurf und Risikofaktoren strukturiert erheben.",
        "icon": "air",
        "tone": "tone-info",
    },
    {
        "key": "B",
        "title": "Brustschmerz",
        "subtitle": "Hausarztpraxisnahes Triage-Szenario",
        "description": "Schmerzcharakter, Ausstrahlung, Belastungsabhaengigkeit und Warnzeichen dokumentieren.",
        "icon": "monitor_heart",
        "tone": "tone-danger",
    },
    {
        "key": "C",
        "title": "Hypertonie-Kontrolle",
        "subtitle": "Auffaelliger Blutdruckwert",
        "description": "Blutdruck, Begleitsymptome, Medikation und Risikofaktoren gezielt abfragen.",
        "icon": "favorite",
        "tone": "tone-warning",
    },
    {
        "key": "D",
        "title": "Typ-2-Diabetes",
        "subtitle": "Metabolische Verlaufskontrolle",
        "description": "Vorbefunde, Komplikationen, Fussprobleme und offene Fragen in Abschnitten sammeln.",
        "icon": "insights",
        "tone": "tone-success",
    },
]

PATIENTS = PatientListClient(
    Path("app/patient_import/patientenTagesliste.json")
).load_patients()


@dataclass
class ChatEntry:
    role: str
    text: str
    tone: str


@dataclass
class BrowserSession:
    identity_check: IdentityCheck = field(
        default_factory=lambda: IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
    )
    current_patient: PatientRecord | None = None
    selected_scenario: str | None = None
    controller: DialogueController | None = None
    stage: str = "login"
    attempts_left: int = MAX_ATTEMPTS
    login_message: str = ""
    login_tone: str = "tone-info"
    messages: list[ChatEntry] = field(default_factory=list)
    pending_input: Callable[[str], None] | None = None
    editing_answers: bool = False
    show_cancel_dialog: bool = False
    login_blocked_until: float | None = None
    avatar_messages: list[ChatEntry] = field(default_factory=list)

    def reset(self) -> None:
        self.identity_check = IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
        self.current_patient = None
        self.selected_scenario = None
        self.controller = None
        self.stage = "login"
        self.attempts_left = MAX_ATTEMPTS
        self.login_message = ""
        self.login_tone = "tone-info"
        self.messages.clear()
        self.pending_input = None
        self.editing_answers = False
        self.show_cancel_dialog = False
        self.login_blocked_until = None
        self.avatar_messages.clear()

    @property
    def has_active_dialogue(self) -> bool:
        return self.controller is not None

    @property
    def summary_ready(self) -> bool:
        return self.controller is not None and self.controller.summary is not None


@dataclass
class _SliderField:
    slider: ui.slider
    unknown_checkbox: ui.checkbox
    min_val: float
    max_val: float
    step: float

    @property
    def value(self) -> str:
        if self.unknown_checkbox.value:
            return "unbekannt"
        return str(int(self.slider.value))


def _classify_message(text: str) -> str:
    normalized = text.upper()
    if "ESKALATION" in normalized or "ACHTUNG" in normalized:
        return "danger"
    if "WARNHINWEIS" in normalized or "[CRITICAL]" in normalized:
        return "warning"
    if "ERFOLGREICH" in normalized or "VIELEN DANK" in normalized:
        return "success"
    return "system"


def _get_current_step(session: BrowserSession) -> int:
    if session.stage == "login":
        return 0
    if session.stage == "scenario":
        return 1
    if session.controller is None:
        return 1

    state = session.controller.state
    if state in (DialogueState.EXPLAIN_ROLE, DialogueState.REQUEST_CONSENT):
        return 2
    if state == DialogueState.ANAMNESIS:
        return 3
    if state in (
        DialogueState.VITAL_PARAMETERS,
        DialogueState.RED_FLAG_CHECK,
        DialogueState.SUMMARY,
        DialogueState.ESCALATION,
    ):
        return 4
    return 5


def _get_process_steps(session: BrowserSession) -> list[tuple[str, str]]:
    labels = [
        "Anmeldung",
        "Szenario",
        "Einwilligung",
        "Anamnese",
        "Auswertung",
        "Abschluss",
    ]
    current_step = _get_current_step(session)
    chips: list[tuple[str, str]] = []

    for index, label in enumerate(labels):
        if index < current_step:
            chips.append((label, "done"))
        elif index == current_step:
            chips.append((label, "active"))
        else:
            chips.append((label, "todo"))

    return chips


def _format_patient_name(patient: PatientRecord | None) -> str:
    if patient is None:
        return "Noch kein Patient angemeldet"
    return f"{patient.first_name} {patient.last_name}"


def _append_system_message(session: BrowserSession, text: str) -> None:
    session.messages.append(
        ChatEntry(role="system", text=text, tone=_classify_message(text))
    )


def _request_dialogue_input(
    session: BrowserSession, callback: Callable[[str], None]
) -> None:
    session.pending_input = callback


def _handle_consent(
    session: BrowserSession, answer: str, refresh_ui: Callable[[], None]
) -> None:
    if session.pending_input is None:
        return
    callback = session.pending_input
    session.pending_input = None
    session.messages.append(
        ChatEntry(role="user", text="Ja" if answer == "ja" else "Nein", tone="user")
    )
    callback(answer)
    refresh_ui()


def _answer_yes_no(
    session: BrowserSession, answer: str, refresh_ui: Callable[[], None]
) -> None:
    if session.pending_input is None:
        return
    session.messages.append(
        ChatEntry(role="user", text=answer, tone="user")
    )
    callback = session.pending_input
    session.pending_input = None
    callback(answer)
    refresh_ui()


def _parse_birth_date(day: str, month: str, year: str) -> date:
    if not (day.isdigit() and month.isdigit() and year.isdigit()):
        raise ValueError(
            "Bitte geben Sie das Geburtsdatum nur mit Zahlen in TT.MM.JJJJ ein."
        )

    if len(year) != 4:
        raise ValueError("Das Jahr muss vierstellig eingegeben werden.")

    try:
        return date(int(year), int(month), int(day))
    except ValueError as exc:
        raise ValueError("Bitte geben Sie ein gültiges Kalenderdatum ein.") from exc


def _render_message(entry: ChatEntry) -> None:
    if not entry.text:
        ui.element("div").classes("h-2")
        return

    alignment = "justify-end" if entry.role == "user" else "justify-start"
    bubble_tone = "chat-bubble--user" if entry.role == "user" else f"chat-bubble--{entry.tone}"
    heading = "Sie" if entry.role == "user" else "Assistenzsystem"

    with ui.row().classes(f"w-full {alignment}"):
        with ui.element("div").classes(f"chat-bubble {bubble_tone}"):
            ui.label(heading).classes(
                "text-[0.74rem] font-bold uppercase tracking-[0.16em] opacity-75"
            )
            ui.label(entry.text).classes("whitespace-pre-wrap text-[0.97rem] leading-7")


def _render_summary_section(title: str, fields: dict[str, str]) -> None:
    with ui.card().classes("surface-card w-full grow min-w-[260px] shadow-none"):
        ui.label(title).classes("text-lg font-semibold")
        for key, value in fields.items():
            with ui.row().classes("w-full items-start justify-between gap-4 py-1"):
                ui.label(key).classes("summary-label")
                ui.label(value or "keine Angabe").classes(
                    "summary-value max-w-[65%] text-right whitespace-pre-wrap"
                )


def main_page() -> None:
    ui.colors(
        primary="#0f766e",
        secondary="#fff0db",
        accent="#17342f",
        positive="#17603d",
        negative="#9f1d20",
        warning="#b55a07",
    )
    ui.add_head_html(STYLE_BLOCK)

    session = BrowserSession()

    def refresh_ui() -> None:
        render_header.refresh()
        render_main.refresh()
        render_sidebar.refresh()

    with ui.column().classes("app-shell gap-6"):
        @ui.refreshable
        def render_header() -> None:
            with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
                with ui.column().classes("gap-2"):
                    ui.label("SET Semesterprojekt").classes("eyebrow")
                    ui.label(PAGE_TITLE).classes("hero-title text-4xl font-bold")
                    ui.label(
                        "Lokale Mehrbenutzer-Oberfläche für strukturierte Voranamnese mit synthetischen Daten."
                    ).classes("max-w-3xl text-[1rem] leading-7 text-slate-600")

                with ui.row().classes("gap-2 flex-wrap"):
                    for label, status in _get_process_steps(session):
                        ui.label(label).classes(f"status-chip status-chip--{status}")

        render_header()

        with ui.row().classes("w-full items-start gap-6 flex-wrap lg:flex-nowrap"):
            with ui.column().classes("min-w-0 grow gap-6"):
                @ui.refreshable
                def render_main() -> None:
                    if session.stage == "login":
                        _render_login(session, refresh_ui)
                    elif session.stage == "scenario":
                        _render_scenario_selection(session, refresh_ui)
                    elif session.editing_answers:
                        _render_answer_editor(session, refresh_ui)
                    else:
                        _render_dialogue(session, refresh_ui)

                    _render_cancel_overlay(session, refresh_ui)
                    _render_login_blocked_overlay(session, refresh_ui)

                render_main()

            with ui.column().classes("w-full gap-6 lg:max-w-[340px]"):
                @ui.refreshable
                def render_sidebar() -> None:
                    _render_sidebar(session, refresh_ui)

                render_sidebar()

def _render_login(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        ui.label("Patientenanmeldung").classes("text-2xl font-semibold")
        ui.label(
            "Bitte melden Sie sich mit Vorname, Nachname und Geburtsdatum an. "
            "Das System dient ausschließlich der strukturierten Vorbereitung für ärztliches Personal."
        ).classes("max-w-3xl text-[1rem] leading-7 text-slate-600")

        ui.label(
            f"Verfügbare Anmeldeversuche: {session.attempts_left}"
        ).classes("status-chip tone-info w-fit")

        if session.login_message:
            ui.label(session.login_message).classes(
                f"w-full rounded-2xl px-4 py-3 text-sm font-medium {session.login_tone}"
            )

        with ui.row().classes("w-full gap-4 flex-wrap"):
            first_name = ui.input("Vorname").props("outlined").classes("min-w-[220px] grow")
            last_name = ui.input("Nachname").props("outlined").classes("min-w-[220px] grow")

        with ui.row().classes("w-full gap-4 flex-wrap items-end"):
            day_input = ui.input("Tag").props("outlined maxlength=2").classes("w-24")
            month_input = ui.input("Monat").props("outlined maxlength=2").classes("w-24")
            year_input = ui.input("Jahr").props("outlined maxlength=4").classes("w-32")

        def submit_login() -> None:
            try:
                parsed_birth_date = _parse_birth_date(
                    (day_input.value or "").strip(),
                    (month_input.value or "").strip(),
                    (year_input.value or "").strip(),
                )
            except ValueError as exc:
                session.login_message = str(exc)
                session.login_tone = "tone-danger"
                refresh_ui()
                return

            if not (first_name.value or "").strip() or not (last_name.value or "").strip():
                session.login_message = "Vorname und Nachname müssen ausgefüllt werden."
                session.login_tone = "tone-danger"
                refresh_ui()
                return

            result = session.identity_check.authenticate(
                (first_name.value or "").strip(),
                (last_name.value or "").strip(),
                parsed_birth_date.isoformat(),
            )
            session.login_message = result.message
            session.login_tone = "tone-success" if result.success else "tone-danger"
            session.attempts_left = result.attempts_left

            if result.success:
                session.current_patient = result.patient
                session.stage = "scenario"
            elif result.escalate:
                session.login_blocked_until = time.time() + 15
                session.identity_check = session.identity_check.__class__(
                    session.identity_check.patients,
                    max_attempts=session.identity_check.max_attempts,
                )
            refresh_ui()

        with ui.row().classes("w-full justify-end gap-3"):
            ui.button("Zurücksetzen", on_click=lambda: (session.reset(), refresh_ui())).props(
                "outline"
            )
            ui.button("Anmelden", on_click=submit_login).props("unelevated").classes(
                "bg-[#0f766e] text-white"
            )


def _render_scenario_selection(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        ui.label("Szenario auswählen").classes("text-2xl font-semibold")
        ui.label(
            f"Angemeldet: {_format_patient_name(session.current_patient)}"
        ).classes("text-[1rem] text-slate-600")

        with ui.row().classes("w-full gap-4 flex-wrap"):
            for scenario in SCENARIOS:
                with ui.card().classes(
                    "surface-card scenario-card min-w-[240px] grow shadow-none"
                ):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon(scenario["icon"]).classes(
                            f"rounded-2xl p-3 text-2xl {scenario['tone']}"
                        )
                        with ui.column().classes("gap-1"):
                            ui.label(f"Szenario {scenario['key']}").classes("eyebrow")
                            ui.label(scenario["title"]).classes("text-lg font-semibold")
                            ui.label(scenario["subtitle"]).classes(
                                "text-sm font-medium text-slate-500"
                            )
                    ui.label(scenario["description"]).classes(
                        "text-[0.95rem] leading-6 text-slate-600"
                    )
                    ui.button(
                        "Szenario starten",
                        on_click=lambda key=scenario["key"]: _start_scenario(
                            session, key, refresh_ui
                        ),
                    ).props("outline").classes("mt-2 w-full")


def _start_scenario(
    session: BrowserSession, scenario_key: str, refresh_ui: Callable[[], None]
) -> None:
    if session.current_patient is None:
        ui.notify("Es ist kein Patient angemeldet.", color="negative")
        return

    session.selected_scenario = scenario_key
    session.messages.clear()
    session.pending_input = None
    session.stage = "dialogue"
    session.controller = DialogueController(
        scenario_key=scenario_key,
        patient=session.current_patient,
        display_message=lambda text: _append_system_message(session, text),
        request_input=lambda callback: _request_dialogue_input(session, callback),
    )
    session.controller.start()
    refresh_ui()


def _render_dialogue(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    if session.controller is None:
        with ui.card().classes("surface-card w-full shadow-none"):
            ui.label("Der Dialog konnte nicht initialisiert werden.").classes(
                "text-lg font-semibold"
            )
            ui.button(
                "Zur Anmeldung zurückkehren",
                on_click=lambda: (session.reset(), refresh_ui()),
            ).props("outline")
        return

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-2"):
                ui.label(session.controller.phase_label).classes("eyebrow")
                ui.label("Assistierte Anamnese").classes("text-2xl font-semibold")
                ui.label(
                    f"Patient: {_format_patient_name(session.current_patient)}"
                ).classes("text-[1rem] text-slate-600")

        if session.controller.state in (
            DialogueState.EXPLAIN_ROLE,
            DialogueState.REQUEST_CONSENT,
        ):
            with ui.card().classes("surface-card w-full shadow-none"):
                ui.label("Einwilligung").classes("text-lg font-semibold")
                ui.label(ROLE_EXPLANATION).classes(
                    "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
                )
                ui.element("div").classes("h-2")
                ui.label(CONSENT_QUESTION).classes(
                    "whitespace-pre-wrap text-[0.97rem] leading-7 font-medium"
                )
                with ui.row().classes("w-full gap-3 justify-center mt-4"):
                    ui.button(
                        "Ja \u2013 Anamnese starten",
                        on_click=lambda: _handle_consent(session, "ja", refresh_ui),
                    ).props("unelevated").classes(
                        "bg-[#0f766e] text-white min-w-[160px]"
                    )
                    ui.button(
                        "Nein \u2013 ablehnen",
                        on_click=lambda: _handle_consent(session, "nein", refresh_ui),
                    ).props("outline").classes(
                        "border-[rgba(159,29,32,0.25)] text-[#9f1d20] min-w-[160px]"
                    )

        elif session.controller.state == DialogueState.ANAMNESIS:
            _render_mass_anamnesis(session, refresh_ui)

        else:
            with ui.scroll_area().classes("chat-shell w-full rounded-3xl bg-white/45 p-4"):
                with ui.column().classes("w-full gap-3"):
                    for entry in session.messages:
                        _render_message(entry)

            current_q = session.controller.current_question
            is_yes_no = current_q is not None and current_q.input_type == "ja_nein"

            if is_yes_no:
                with ui.row().classes("w-full gap-3 justify-center mt-2"):
                    ui.button(
                        "Ja",
                        on_click=lambda: _answer_yes_no(session, "ja", refresh_ui),
                    ).props("unelevated").classes(
                        "bg-[#0f766e] text-white min-w-[120px]"
                    )
                    ui.button(
                        "Nein",
                        on_click=lambda: _answer_yes_no(session, "nein", refresh_ui),
                    ).props("outline").classes(
                        "border-[rgba(159,29,32,0.25)] text-[#9f1d20] min-w-[120px]"
                    )

                def cancel_yes_no() -> None:
                    if session.pending_input is None:
                        return
                    session.messages.append(
                        ChatEntry(role="user", text="abbrechen", tone="user")
                    )
                    callback = session.pending_input
                    session.pending_input = None
                    callback("abbrechen")
                    refresh_ui()

                with ui.row().classes("w-full justify-center mt-2"):
                    ui.button(
                        "Abbrechen", on_click=cancel_yes_no
                    ).props("outline dense").classes(
                        "text-xs border-[rgba(159,29,32,0.25)] text-[#9f1d20]"
                    )
            else:
                def submit_answer() -> None:
                    if session.pending_input is None:
                        return

                    answer = (answer_input.value or "").strip()
                    session.messages.append(
                        ChatEntry(
                            role="user",
                            text=answer or "(keine Angabe)",
                            tone="user",
                        )
                    )
                    callback = session.pending_input
                    session.pending_input = None
                    answer_input.value = ""
                    callback(answer)
                    refresh_ui()

                def cancel_dialogue() -> None:
                    if session.pending_input is None:
                        return
                    answer_input.value = "abbrechen"
                    submit_answer()

                answer_input = ui.input("Ihre Antwort").props("outlined").classes("w-full")
                answer_input.on("keydown.enter", lambda _: submit_answer())

                with ui.row().classes("w-full justify-end gap-3"):
                    cancel_button = ui.button(
                        "Abbrechen", on_click=cancel_dialogue
                    ).props("outline").classes(
                        "border-[rgba(159,29,32,0.25)] text-[#9f1d20]"
                    )
                    send_button = ui.button("Senden", on_click=submit_answer).props(
                        "unelevated"
                    ).classes("bg-[#0f766e] text-white")

                if session.pending_input is None:
                    answer_input.disable()
                    send_button.disable()
                    cancel_button.disable()

    if session.summary_ready:
        _render_summary(session, refresh_ui)


def _render_summary(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    if session.controller is None or session.controller.summary is None:
        return

    summary = session.controller.summary

    with ui.card().classes("surface-card w-full shadow-none"):
        ui.label("Strukturierte Zusammenfassung").classes("text-2xl font-semibold")
        ui.label(
            "Die Ergebnisdarstellung ist abschnittsweise gegliedert und für die ärztliche Übergabe gedacht."
        ).classes("text-[1rem] leading-7 text-slate-600")

        with ui.row().classes("w-full gap-4 flex-wrap"):
            _render_summary_section(
                "Metadaten",
                {
                    "Patient": summary.patient_name,
                    "Patienten-ID": summary.patient_id,
                    "Szenario": summary.scenario,
                    "Zeitpunkt": summary.timestamp,
                },
            )

            _render_summary_section(
                "Vitalparameter",
                {
                    "Quelle": summary.vitals_source,
                    **{key: str(value) for key, value in summary.vitals.items()},
                },
            )

        if summary.grouped_sections:
            for title, fields in summary.grouped_sections.items():
                _render_summary_section(title, fields)
        else:
            _render_summary_section("Anamnese-Antworten", summary.answers)

        if summary.red_flags:
            _render_summary_section(
                "Red Flags",
                {
                    rf.rule_id: f"{rf.severity}: {rf.description}"
                    for rf in summary.red_flags
                },
            )

        if summary.open_points:
            _render_summary_section(
                "Offene Punkte",
                {f"Punkt {index + 1}": point for index, point in enumerate(summary.open_points)},
            )

        with ui.row().classes("w-full justify-center gap-3 mt-6"):
            ui.button(
                "Antworten bearbeiten",
                on_click=lambda: _start_editing(session, refresh_ui),
            ).props("unelevated").classes("bg-[#0f766e] text-white min-w-[200px]")


def _start_editing(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.editing_answers = True
    refresh_ui()


def _build_question_form(
    controller: DialogueController,
    questions_with_answers: list[tuple],
    title: str,
    description: str,
    submit_label: str,
    submit_callback: Callable[[dict[str, str]], None],
    cancel_callback: Callable[[], None],
    live_visibility: bool = True,
) -> None:
    if controller is None:
        return

    containers: dict[str, ui.card] = {}
    fields: dict[str, object] = {}
    q_text_map: dict[str, str] = {q.key: q.text for q, _ in questions_with_answers}
    input_types: dict[str, str] = {q.key: q.input_type for q, _ in questions_with_answers}
    required_keys: set[str] = {q.key for q, _ in questions_with_answers if q.required}

    def _make_radio_handler(key: str):
        def _handler(e) -> None:
            if live_visibility:
                for q, _ in questions_with_answers:
                    if q.key in containers:
                        containers[q.key].visible = controller.is_question_visible(
                            q.key, {k: (f.value if hasattr(f, 'value') else f) for k, f in fields.items()}
                        )
        return _handler

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            ui.label(title).classes("text-2xl font-semibold")
            ui.label(description).classes("text-[1rem] leading-7 text-slate-600")

        for question, answer in questions_with_answers:
            key = question.key
            label = question.text
            if key in required_keys:
                label = f"{label} *"

            with ui.card().classes("surface-card w-full shadow-none") as card:
                containers[key] = card
                ui.label(label).classes(
                    "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
                )

                if question.input_type == "ja_nein":
                    radio = ui.radio(
                        ["Ja", "Nein"],
                        value=answer if answer in ("Ja", "Nein") else None,
                    ).props("inline")
                    radio.on("update:model-value", _make_radio_handler(key))
                    fields[key] = radio
                elif question.input_type == "zahl":
                    has_slider = (
                        question.slider_min is not None
                        and question.slider_max is not None
                    )
                    if has_slider:
                        min_val = float(question.slider_min)
                        max_val = float(question.slider_max)
                        step = float(question.slider_step or 1)

                        try:
                            init_val = float(answer.replace(",", "."))
                        except (ValueError, AttributeError):
                            init_val = min_val

                        init_val = max(min_val, min(max_val, init_val))

                        with ui.column().classes("w-full gap-1"):
                            slider = ui.slider(
                                min=min_val, max=max_val, step=step, value=init_val
                            ).classes("w-full")
                            value_label = ui.label(f"Wert: {int(init_val)}").classes(
                                "text-sm font-medium text-center"
                            )
                            slider.on(
                                "update:model-value",
                                lambda e, lbl=value_label: lbl.set_text(
                                    f"Wert: {int(float(e.args))}"
                                ),
                            )

                            unknown_checkbox = ui.checkbox("unbekannt")
                            unknown_checkbox.on(
                                "update:model-value",
                                lambda e, s=slider: (
                                    s.disable() if e.args else s.enable()
                                ),
                            )

                        fields[key] = _SliderField(
                            slider, unknown_checkbox, min_val, max_val, step
                        )
                    else:
                        inp = ui.input(
                            value=answer,
                            placeholder="Zahl eingeben oder 'unbekannt'",
                        ).classes("w-full").props("outlined")
                        fields[key] = inp
                else:
                    ta = ui.textarea(
                        value=answer,
                        placeholder="Ihre Antwort",
                    ).classes("w-full").props("outlined")
                    fields[key] = ta

        if live_visibility:
            for q, _ in questions_with_answers:
                if q.key in containers:
                    collected_now = {
                        k: (str(f.value).strip() if f.value is not None else "")
                        for k, f in fields.items()
                    }
                    containers[q.key].visible = controller.is_question_visible(
                        q.key, collected_now
                    )

        def _collect_and_validate() -> list[str]:
            collected: dict[str, str] = {}
            errors: list[str] = []

            for key, field in fields.items():
                value = field.value
                if value is None:
                    value = ""
                collected[key] = str(value).strip()

            for key in required_keys:
                if not collected.get(key, "") and controller.is_question_visible(key, collected):
                    errors.append(f"'{q_text_map[key]}' ist erforderlich und wurde nicht ausgefüllt.")

            for key, value in collected.items():
                it = input_types.get(key)
                if it == "ja_nein" and value and value not in ("Ja", "Nein"):
                    errors.append(
                        f"'{q_text_map[key]}' muss mit 'Ja' oder 'Nein' beantwortet werden."
                    )
                elif it == "zahl" and value and value.lower() != "unbekannt":
                    try:
                        float(value.replace(",", "."))
                    except ValueError:
                        errors.append(
                            f"'{q_text_map[key]}' muss eine Zahl oder 'unbekannt' sein."
                        )

            return errors

        def _on_submit() -> None:
            errors = _collect_and_validate()
            if errors:
                ui.notify(
                    "Bitte korrigieren Sie folgende Fehler:\n" + "\n".join(errors),
                    color="negative",
                    multi_line=True,
                )
                return
            collected = {
                k: (str(f.value).strip() if f.value is not None else "")
                for k, f in fields.items()
            }
            submit_callback(collected)

        with ui.row().classes("w-full justify-end gap-3"):
            ui.button(
                "Abbrechen", on_click=cancel_callback
            ).props("outline").classes(
                "border-[rgba(159,29,32,0.25)] text-[#9f1d20]"
            )
            ui.button(
                submit_label, on_click=_on_submit
            ).props("unelevated").classes("bg-[#0f766e] text-white")


def _render_cancel_overlay(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if not session.show_cancel_dialog or session.controller is None:
        return

    with ui.element("div").classes("fixed inset-0 bg-black/40 z-50"):
        with ui.card().classes(
            "surface-card shadow-none border-2 border-[#9f1d20]"
        ).style(
            "position: fixed; top: 50%; left: 50%; "
            "transform: translate(-50%, -50%); z-index: 51;"
        ):
            ui.label("Abbrechen best\u00e4tigen").classes("text-lg font-semibold")
            ui.label(
                "Sind Sie sicher, dass Sie die Anamnese beenden wollen?\n"
                "Alle nicht gespeicherten Angaben gehen verloren."
            ).classes(
                "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
            )
            with ui.row().classes("w-full gap-3 justify-center mt-4"):
                ui.button(
                    "Ja, abbrechen",
                    on_click=lambda: _confirm_cancel_anamnesis(session, refresh_ui),
                ).props("unelevated").classes(
                    "bg-[#9f1d20] text-white min-w-[140px]"
                )
                ui.button(
                    "Nein, weiter",
                    on_click=lambda: _dismiss_cancel_dialog(session, refresh_ui),
                ).props("outline").classes(
                    "border-[rgba(159,29,32,0.25)] text-[#9f1d20] min-w-[140px]"
                )


def _confirm_cancel_anamnesis(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.controller is None:
        return
    session.show_cancel_dialog = False
    session.controller = None
    session.messages.clear()
    session.pending_input = None
    session.stage = "scenario"
    refresh_ui()


def _dismiss_cancel_dialog(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.show_cancel_dialog = False
    refresh_ui()


def _render_login_blocked_overlay(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.login_blocked_until is None:
        return
    remaining = session.login_blocked_until - time.time()
    if remaining <= 0:
        session.login_blocked_until = None
        session.login_message = ""
        session.login_tone = ""
        refresh_ui()
        return

    with ui.element("div").classes("fixed inset-0 bg-black/40 z-50"):
        with ui.card().classes(
            "surface-card shadow-none border-2 border-[#9f1d20]"
        ).style(
            "position: fixed; top: 50%; left: 50%; "
            "transform: translate(-50%, -50%); z-index: 51;"
        ):
            ui.label("Anmeldung gesperrt").classes("text-lg font-semibold")
            ui.label(
                "Die Identität konnte nach drei Versuchen nicht bestätigt werden.\n"
                "Das Fenster schließt sich automatisch.\n"
                "Bitte wenden Sie sich an das Praxispersonal."
            ).classes(
                "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
            )

    ui.timer(1, once=True, callback=refresh_ui)


def _render_avatar(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    if session.controller is None:
        return
    if session.controller.state != DialogueState.ANAMNESIS:
        return

    with ui.card().classes("surface-card w-full shadow-none avatar-container"):
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("\U0001fa7a").classes("avatar-bounce").style(
                "font-size: 40px; line-height: 1; cursor: pointer;"
            ).on("click", lambda: _on_avatar_click())
            with ui.column().classes("gap-0"):
                ui.label("Arzt-Assistent").classes("text-sm font-semibold")
                ui.label("Ich helfe Ihnen gern.").classes(
                    "text-xs text-slate-500"
                )

        if not session.avatar_messages:
            session.avatar_messages.append(
                ChatEntry(
                    role="system",
                    text="Guten Tag, ich bin Ihr digitaler Assistent f\u00fcr die Anamnese.",
                    tone="system",
                )
            )

        with ui.scroll_area().classes("w-full").style(
            "max-height: 300px; overflow-y: auto; margin-top: 8px;"
        ):
            with ui.column().classes("w-full gap-2"):
                for msg in session.avatar_messages:
                    _render_message(msg)


def _on_avatar_click() -> None:
    ui.notify(
        "Willkommen, ich bin Ihr digitaler Assistent.",
        color="info",
        position="bottom-right",
    )


def _render_mass_anamnesis(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.controller is None:
        return

    questions_with_answers = session.controller.get_questions_with_answers()

    def _on_submit(answers: dict[str, str]) -> None:
        try:
            session.controller.submit_mass_anamnesis(answers)
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    def _on_cancel() -> None:
        session.show_cancel_dialog = True
        refresh_ui()

    _build_question_form(
        controller=session.controller,
        questions_with_answers=questions_with_answers,
        title="Anamnese",
        description=(
            "Alle Fragen auf einen Blick. Pflichtfelder sind mit * markiert. "
            "Einige Fragen werden dynamisch ein- oder ausgeblendet."
        ),
        submit_label="Absenden",
        submit_callback=_on_submit,
        cancel_callback=_on_cancel,
        live_visibility=True,
    )


def _render_answer_editor(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.controller is None:
        return

    questions_with_answers = session.controller.get_questions_with_answers()

    def _on_submit(answers: dict[str, str]) -> None:
        try:
            session.controller.update_answers_and_regenerate(answers)
            session.editing_answers = False
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    _build_question_form(
        controller=session.controller,
        questions_with_answers=questions_with_answers,
        title="Antworten bearbeiten",
        description=(
            "Alle Fragen auf einen Blick. Aenderungen werden nach dem Speichern "
            "in die Zusammenfassung uebernommen."
        ),
        submit_label="Speichern",
        submit_callback=_on_submit,
        cancel_callback=lambda: _cancel_editing(session, refresh_ui),
        live_visibility=True,
    )


def _cancel_editing(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.editing_answers = False
    refresh_ui()


def _render_sidebar(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    with ui.card().classes("surface-card w-full shadow-none"):
        ui.label("Sitzung").classes("eyebrow")
        ui.label(_format_patient_name(session.current_patient)).classes(
            "text-xl font-semibold"
        )
        ui.label(
            "Jede Browser-Sitzung fuehrt ihren eigenen Login- und Dialogzustand."
        ).classes("text-sm leading-6 text-slate-600")

        if session.current_patient is not None:
            ui.label(f"Patienten-ID: {session.current_patient.patient_id}").classes(
                "text-sm text-slate-500"
            )

        if session.controller is not None:
            ui.label(f"Aktuelle Phase: {session.controller.phase_label}").classes(
                "status-chip tone-info w-fit"
            )

        with ui.row().classes("w-full gap-3"):
            ui.button("Neu starten", on_click=lambda: (session.reset(), refresh_ui())).props(
                "outline"
            ).classes("grow")
            if session.stage == "scenario":
                ui.button(
                    "Abmelden",
                    on_click=lambda: (session.reset(), refresh_ui()),
                ).props("outline").classes("grow")

    _render_avatar(session, refresh_ui)

    if session.controller is not None and session.controller.export_path is not None:
        with ui.card().classes("surface-card w-full shadow-none"):
            ui.label("Export").classes("eyebrow")
            ui.label(str(session.controller.export_path)).classes(
                "break-all text-sm leading-6 text-slate-600"
            )

def run_app() -> None:
    ui.run(
        root=main_page,
        host="127.0.0.1",
        port=8080,
        title=PAGE_TITLE,
        reload=False,
        show=False,
    )
