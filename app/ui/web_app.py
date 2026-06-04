from __future__ import annotations

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

    @property
    def has_active_dialogue(self) -> bool:
        return self.controller is not None

    @property
    def summary_ready(self) -> bool:
        return self.controller is not None and self.controller.summary is not None


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
        ChatEntry(role="user", text="ja" if answer == "ja" else "nein", tone="user")
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
        raise ValueError("Bitte geben Sie ein gueltiges Kalenderdatum ein.") from exc


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
                        "Lokale Mehrbenutzer-Oberflaeche fuer strukturierte Voranamnese mit synthetischen Daten."
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
                    else:
                        _render_dialogue(session, refresh_ui)

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
            "Das System dient ausschliesslich der strukturierten Vorbereitung fuer aerztliches Personal."
        ).classes("max-w-3xl text-[1rem] leading-7 text-slate-600")

        ui.label(
            f"Verfuegbare Anmeldeversuche: {session.attempts_left}"
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
                session.login_message = "Vorname und Nachname muessen ausgefuellt werden."
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
            refresh_ui()

        with ui.row().classes("w-full justify-end gap-3"):
            ui.button("Zuruecksetzen", on_click=lambda: (session.reset(), refresh_ui())).props(
                "outline"
            )
            ui.button("Anmelden", on_click=submit_login).props("unelevated").classes(
                "bg-[#0f766e] text-white"
            )


def _render_scenario_selection(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        ui.label("Szenario auswaehlen").classes("text-2xl font-semibold")
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
                "Zur Anmeldung zurueckkehren",
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

            if session.controller.state == DialogueState.ANAMNESIS:
                current_question, total_questions = session.controller.question_progress
                with ui.card().classes("shadow-none border border-[rgba(15,118,110,0.12)]"):
                    ui.label("Fragenfortschritt").classes("summary-label")
                    ui.label(
                        f"Frage {current_question} von {total_questions}"
                    ).classes("text-lg font-semibold")
                    progress_value = (
                        current_question / total_questions if total_questions else 0
                    )
                    ui.linear_progress(value=progress_value).classes("w-48")
                    pct = round(progress_value * 100)
                    ui.label(f"{pct}%").classes("text-sm text-slate-500")
                    ui.label(
                        "Die Anzeige passt sich an optionale Folgefragen im Verlauf an."
                    ).classes("text-xs text-slate-500")

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
            current_q = session.controller.current_question
            with ui.card().classes("surface-card w-full shadow-none"):
                ui.label("Aktuelle Frage").classes("text-lg font-semibold")
                if current_q:
                    ui.label(current_q.text).classes(
                        "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
                    )

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

                def cancel_yes_no_an() -> None:
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
                        "Abbrechen", on_click=cancel_yes_no_an
                    ).props("outline dense").classes(
                        "text-xs border-[rgba(159,29,32,0.25)] text-[#9f1d20]"
                    )
            else:
                def submit_answer_an() -> None:
                    if session.pending_input is None:
                        return

                    answer = (answer_input_an.value or "").strip()
                    session.messages.append(
                        ChatEntry(
                            role="user",
                            text=answer or "(keine Angabe)",
                            tone="user",
                        )
                    )
                    callback = session.pending_input
                    session.pending_input = None
                    answer_input_an.value = ""
                    callback(answer)
                    refresh_ui()

                def cancel_dialogue_an() -> None:
                    if session.pending_input is None:
                        return
                    answer_input_an.value = "abbrechen"
                    submit_answer_an()

                answer_input_an = ui.input("Ihre Antwort").props("outlined").classes("w-full")
                answer_input_an.on("keydown.enter", lambda _: submit_answer_an())

                with ui.row().classes("w-full justify-end gap-3"):
                    cancel_button_an = ui.button(
                        "Abbrechen", on_click=cancel_dialogue_an
                    ).props("outline").classes(
                        "border-[rgba(159,29,32,0.25)] text-[#9f1d20]"
                    )
                    send_button_an = ui.button("Senden", on_click=submit_answer_an).props(
                        "unelevated"
                    ).classes("bg-[#0f766e] text-white")

                if session.pending_input is None:
                    answer_input_an.disable()
                    send_button_an.disable()
                    cancel_button_an.disable()

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
        _render_summary(session)


def _render_summary(session: BrowserSession) -> None:
    if session.controller is None or session.controller.summary is None:
        return

    summary = session.controller.summary

    with ui.card().classes("surface-card w-full shadow-none"):
        ui.label("Strukturierte Zusammenfassung").classes("text-2xl font-semibold")
        ui.label(
            "Die Ergebnisdarstellung ist abschnittsweise gegliedert und fuer die aerztliche Uebergabe gedacht."
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

    with ui.card().classes("surface-card w-full shadow-none"):
        ui.label("Prozess").classes("eyebrow")
        for label, status in _get_process_steps(session):
            ui.label(label).classes(f"status-chip status-chip--{status} w-fit")

    if session.controller is not None and session.controller.state == DialogueState.ANAMNESIS:
        with ui.card().classes("surface-card w-full shadow-none"):
            current_question, total_questions = session.controller.question_progress
            ui.label("Anamnese-Fortschritt").classes("eyebrow")
            ui.label(f"{current_question} von {total_questions} Fragen").classes(
                "text-xl font-semibold"
            )
            progress_value = current_question / total_questions if total_questions else 0
            ui.linear_progress(value=progress_value).classes("w-full")
            pct = round(progress_value * 100)
            ui.label(f"{pct}%").classes("text-sm leading-6 text-slate-600")
            ui.label(
                f"Bereits angezeigte Fragen: {session.controller.asked_question_count}"
            ).classes("text-sm leading-6 text-slate-600")

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
