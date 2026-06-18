from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime

from app.devices.simulators import Simulator
from pathlib import Path
from typing import Callable

try:
    from nicegui import ui
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "NiceGUI ist nicht installiert. Bitte zuerst 'pip install -r requirements.txt' ausführen."
    ) from exc

from app.ai.symptom_extractor import extract_answers
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
from app.patient_import.patient_schema import PatientDetails, PatientRecord
from app.output.export_pdf import export_summary_pdf

MAX_ATTEMPTS = 3
PAGE_TITLE = "KI-gestützter Anamnese-Agent"
PERSONAL_PAGE_TITLE = "SET Personalmodus"
PATIENT_MODE = "patient"
PERSONAL_MODE = "personal"
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

    .sticky-summary-actions {
        position: sticky;
        top: 12px;
        z-index: 40;
        background: rgba(255, 250, 242, 0.92);
        border: 1px solid var(--app-border);
        border-radius: 22px;
        box-shadow: 0 16px 30px rgba(30, 65, 60, 0.10);
        backdrop-filter: blur(10px);
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

    .avatar-panel {
        background: linear-gradient(135deg, rgba(214, 239, 233, 0.95), rgba(255, 240, 219, 0.92));
        border: 1px solid rgba(23, 52, 47, 0.08);
        border-radius: 28px;
        padding: 18px;
    }

    .owl-avatar {
        --owl-feather: #236f68;
        --owl-feather-dark: #174b47;
        --owl-face: #f6ead7;
        --owl-chest: #fffaf2;
        --owl-beak: #c98737;
        --owl-shadow: rgba(15, 73, 68, 0.2);
        width: 84px;
        height: 84px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: none;
        border-radius: 999px;
        background:
            radial-gradient(circle at 38% 32%, rgba(255, 255, 255, 0.38), transparent 28%),
            linear-gradient(145deg, rgba(255, 250, 242, 0.72), rgba(214, 239, 233, 0.8));
        box-shadow: 0 16px 32px var(--owl-shadow);
        cursor: default;
        transform-origin: center bottom;
        animation: owl-idle 4s ease-in-out infinite;
    }

    .owl-avatar--small {
        width: 58px;
        height: 58px;
    }

    .owl-avatar--medium {
        width: 64px;
        height: 64px;
    }

    .owl-avatar__svg {
        width: 100%;
        height: 100%;
        overflow: visible;
    }

    .owl-avatar__head {
        transform-box: fill-box;
        transform-origin: center bottom;
    }

    .owl-avatar__tufts,
    .owl-avatar__face {
        fill: var(--owl-feather);
    }

    .owl-avatar__wing {
        fill: var(--owl-feather-dark);
        opacity: 0.34;
    }

    .owl-avatar__mask {
        fill: var(--owl-face);
    }

    .owl-avatar__chest,
    .owl-avatar__coat {
        fill: var(--owl-chest);
    }

    .owl-avatar__coat-line {
        fill: none;
        stroke: rgba(23, 52, 47, 0.2);
        stroke-width: 2;
        stroke-linecap: round;
    }

    .owl-avatar__eye-white {
        fill: #fffdfa;
    }

    .owl-avatar__pupil {
        fill: #17342f;
        transform-box: fill-box;
        transform-origin: center;
        transition: transform 0.18s ease;
    }

    .owl-avatar__catchlight {
        fill: #ffffff;
        opacity: 0.9;
    }

    .owl-avatar__lid {
        fill: var(--owl-face);
        transform-box: fill-box;
        transform-origin: center;
        animation: owl-blink 5.6s ease-in-out infinite;
    }

    .owl-avatar__brow {
        fill: none;
        stroke: rgba(23, 52, 47, 0.42);
        stroke-width: 3;
        stroke-linecap: round;
        transform-box: fill-box;
        transform-origin: center;
        transition: transform 0.2s ease;
    }

    .owl-avatar__beak {
        fill: var(--owl-beak);
        transform-box: fill-box;
        transform-origin: center top;
    }

    .owl-avatar__mouth-inside {
        fill: #5a3428;
        opacity: 0;
    }

    .owl-avatar__beak-open,
    .owl-avatar__beak-wide {
        opacity: 0;
    }

    .owl-avatar__smile {
        fill: none;
        stroke: rgba(23, 52, 47, 0.42);
        stroke-width: 2.4;
        stroke-linecap: round;
        opacity: 0;
    }

    .owl-avatar__badge {
        fill: #d6efe9;
        stroke: rgba(23, 52, 47, 0.12);
        stroke-width: 1.5;
    }

    .owl-avatar__badge-cross {
        fill: none;
        stroke: #236f68;
        stroke-width: 2.1;
        stroke-linecap: round;
    }

    .owl-avatar__thought-dot {
        fill: #fffaf2;
        stroke: rgba(23, 52, 47, 0.16);
        stroke-width: 1.3;
        opacity: 0;
    }

    .owl-avatar--thinking {
        --owl-feather: #776e52;
        --owl-feather-dark: #4e4939;
        --owl-beak: #b87933;
    }

    .owl-avatar--thinking .owl-avatar__head {
        transform: rotate(-4deg) translateY(1px);
    }

    .owl-avatar--thinking .owl-avatar__pupil {
        transform: translate(2px, -2px);
    }

    .owl-avatar--thinking .owl-avatar__thought-dot {
        opacity: 1;
        animation: owl-thought 1.8s ease-in-out infinite;
    }

    .owl-avatar--listening .owl-avatar__head {
        animation: owl-listen 2.4s ease-in-out infinite;
    }

    .owl-avatar--listening .owl-avatar__pupil {
        transform: translate(0, 1px);
    }

    .owl-avatar--alert {
        --owl-feather: #7f3234;
        --owl-feather-dark: #5d2426;
        --owl-beak: #b55a07;
        --owl-shadow: rgba(127, 50, 52, 0.2);
        background: linear-gradient(145deg, #fff7ed, #fde8e8);
    }

    .owl-avatar--alert .owl-avatar__brow-left {
        transform: rotate(14deg) translateY(2px);
    }

    .owl-avatar--alert .owl-avatar__brow-right {
        transform: rotate(-14deg) translateY(2px);
    }

    .owl-avatar--done {
        --owl-feather: #2d7050;
        --owl-feather-dark: #1e513a;
        --owl-beak: #bd8741;
        --owl-shadow: rgba(45, 112, 80, 0.18);
    }

    .owl-avatar--done .owl-avatar__smile {
        opacity: 1;
    }

    .owl-avatar--done .owl-avatar__pupil {
        transform: translateY(-1px);
    }

    body.avatar-is-speaking .owl-avatar .owl-avatar__head {
        animation: owl-speak-nod 1.4s ease-in-out infinite;
    }

    body.avatar-is-speaking .owl-avatar .owl-avatar__beak-closed {
        animation: owl-mouth-closed 0.6s steps(1, end) infinite;
        transform: translateY(-1px) scaleY(0.82);
    }

    body.avatar-is-speaking .owl-avatar .owl-avatar__beak-open {
        animation: owl-mouth-open 0.6s steps(1, end) infinite;
    }

    body.avatar-is-speaking .owl-avatar .owl-avatar__beak-wide {
        animation: owl-mouth-wide 0.6s steps(1, end) infinite;
    }

    body.avatar-is-speaking .owl-avatar .owl-avatar__mouth-inside {
        animation: owl-mouth-inside 0.6s steps(1, end) infinite;
    }

    body.avatar-is-speaking .owl-avatar .owl-avatar__lid {
        animation-duration: 4.4s;
    }

    @keyframes owl-idle {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-2px); }
    }

    @keyframes owl-listen {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(2px); }
    }

    @keyframes owl-speak-nod {
        0%, 100% { transform: translateY(0) rotate(0deg); }
        35% { transform: translateY(2px) rotate(-1deg); }
        70% { transform: translateY(1px) rotate(1deg); }
    }

    @keyframes owl-blink {
        0%, 93%, 100% { transform: scaleY(0); }
        95%, 97% { transform: scaleY(1); }
    }

    @keyframes owl-mouth-closed {
        0%, 20%, 76%, 100% { opacity: 1; }
        21%, 75% { opacity: 0; }
    }

    @keyframes owl-mouth-open {
        0%, 20%, 48%, 76%, 100% { opacity: 0; }
        21%, 47% { opacity: 1; }
    }

    @keyframes owl-mouth-wide {
        0%, 48%, 76%, 100% { opacity: 0; }
        49%, 75% { opacity: 1; }
    }

    @keyframes owl-mouth-inside {
        0%, 20%, 76%, 100% { opacity: 0; }
        21%, 47% { opacity: 0.62; }
        49%, 75% { opacity: 0.82; }
    }

    @keyframes owl-thought {
        0%, 100% { transform: translateY(0); opacity: 0.42; }
        50% { transform: translateY(-3px); opacity: 1; }
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
        "description": "Schmerzcharakter, Ausstrahlung, Belastungsabhängigkeit und Warnzeichen dokumentieren.",
        "icon": "monitor_heart",
        "tone": "tone-danger",
    },
    {
        "key": "C",
        "title": "Hypertonie-Kontrolle",
        "subtitle": "Auffälliger Blutdruckwert",
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
    entry_mode: str = PATIENT_MODE
    identity_check: IdentityCheck = field(
        default_factory=lambda: IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
    )
    current_patient: PatientRecord | None = None
    selected_scenario: str | None = None
    controller: DialogueController | None = None
    selected_scenarios: list[str] = field(default_factory=list)
    controllers: list[DialogueController] = field(default_factory=list)
    stage: str = "login"
    attempts_left: int = MAX_ATTEMPTS
    login_message: str = ""
    login_tone: str = "tone-info"
    messages: list[ChatEntry] = field(default_factory=list)
    pending_input: Callable[[str], None] | None = None
    editing_answers: bool = False
    show_cancel_dialog: bool = False
    show_reject_consent_dialog: bool = False
    login_blocked_until: float | None = None
    avatar_messages: list[ChatEntry] = field(default_factory=list)
    chat_input_text: str = ""
    prefilled_answers: dict[str, str] = field(default_factory=dict)
    chat_phase_done: bool = False
    anamnesis_mode: str | None = None
    speech_enabled: bool = True
    simulated_bp: dict | None = None
    simulated_weight: dict | None = None
    simulated_oximeter: dict | None = None
    spoken_message_count: int = 0
    staff_search_query: str = ""

    def reset(self) -> None:
        self.identity_check = IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
        self.current_patient = None
        self.selected_scenario = None
        self.controller = None
        self.selected_scenarios.clear()
        self.controllers.clear()
        self.stage = "staff_selection" if self.entry_mode == PERSONAL_MODE else "login"
        self.attempts_left = MAX_ATTEMPTS
        self.login_message = ""
        self.login_tone = "tone-info"
        self.messages.clear()
        self.pending_input = None
        self.editing_answers = False
        self.show_cancel_dialog = False
        self.show_reject_consent_dialog = False
        self.login_blocked_until = None
        self.avatar_messages.clear()
        self.chat_input_text = ""
        self.prefilled_answers.clear()
        self.chat_phase_done = False
        self.anamnesis_mode = None
        self.speech_enabled = True
        self.simulated_bp = None
        self.simulated_weight = None
        self.simulated_oximeter = None
        self.spoken_message_count = 0
        self.staff_search_query = ""

    @property
    def primary_controller(self) -> DialogueController | None:
        return self.controllers[0] if self.controllers else self.controller

    @property
    def has_active_dialogue(self) -> bool:
        return self.primary_controller is not None

    @property
    def summary_ready(self) -> bool:
        ctrl = self.primary_controller
        return ctrl is not None and ctrl.summary is not None

    @property
    def is_personal_mode(self) -> bool:
        return self.entry_mode == PERSONAL_MODE


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
    if session.stage == "staff_selection":
        return 0
    if session.stage == "login":
        return 1 if session.is_personal_mode else 0
    if session.stage == "scenario":
        return 1
    ctrl = session.primary_controller
    if ctrl is None:
        return 1

    state = ctrl.state
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
    if session.is_personal_mode:
        labels = [
            "Tagesliste",
            "Identität",
            "Einwilligung",
            "Anamnese",
            "Auswertung",
            "Abschluss",
        ]
    else:
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


def _format_display_date(raw_value: str) -> str:
    if not raw_value:
        return "keine Angabe"
    try:
        return date.fromisoformat(raw_value).strftime("%d.%m.%Y")
    except ValueError:
        return raw_value


def _format_display_datetime(raw_value: str) -> str:
    if not raw_value:
        return "keine Angabe"
    try:
        return datetime.fromisoformat(raw_value).strftime("%d.%m.%Y, %H:%M")
    except ValueError:
        return raw_value


def _format_detail_value(raw_value: str) -> str:
    if not raw_value:
        return "keine Angabe"
    mapping = {
        "weiblich": "Weiblich",
        "männlich": "Männlich",
        "divers": "Divers",
        "de": "Deutsch",
        "aktiv": "Aktiv",
    }
    return mapping.get(raw_value, raw_value)


def _format_next_appointment(patient: PatientRecord) -> str:
    parts: list[str] = []
    if patient.details.next_appointment_at:
        parts.append(_format_display_datetime(patient.details.next_appointment_at))
    if patient.details.next_appointment_type:
        parts.append(patient.details.next_appointment_type)
    return " - ".join(parts) if parts else "keine Angabe"


def _summarize_values(values: list[str] | tuple[str, ...], limit: int = 2) -> str:
    if not values:
        return "keine Angabe"
    items = list(values)
    if len(items) <= limit:
        return ", ".join(items)
    return ", ".join(items[:limit]) + f" +{len(items) - limit} weitere"


def _patient_matches_staff_search(patient: PatientRecord, query: str) -> bool:
    normalized_query = query.strip().casefold()
    if not normalized_query:
        return True

    search_values = [
        _format_patient_name(patient),
        patient.date_of_birth,
        _format_display_date(patient.date_of_birth),
        patient.patient_id,
    ]
    combined = " ".join(search_values).casefold()
    return normalized_query in combined


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

    if answer == "ja":
        consent_value = "ja"
        for ctrl in session.controllers:
            if ctrl.state == DialogueState.REQUEST_CONSENT:
                ctrl._display(CONSENT_ACCEPTED)
                ctrl._state_machine.advance()
                ctrl._handle_state()

        callback = session.pending_input
        session.pending_input = None
        session.messages.append(
            ChatEntry(role="user", text="Ja", tone="user")
        )
        callback(consent_value)
        refresh_ui()
    else:
        session.show_reject_consent_dialog = True
        refresh_ui()


def _confirm_reject_consent(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.show_reject_consent_dialog = False
    for ctrl in session.controllers:
        if ctrl.state == DialogueState.REQUEST_CONSENT:
            ctrl._display(CONSENT_DECLINED)
            ctrl._state_machine.jump_to(DialogueState.END)
            ctrl._handle_state()
    callback = session.pending_input
    session.pending_input = None
    session.messages.append(
        ChatEntry(role="user", text="Nein", tone="user")
    )
    if callback:
        callback("nein")
    session.controller = None
    session.controllers.clear()
    session.selected_scenarios.clear()
    session.messages.clear()
    session.anamnesis_mode = None
    session.chat_phase_done = False
    session.prefilled_answers.clear()
    session.current_patient = None
    session.login_message = ""
    session.login_tone = "tone-info"
    session.attempts_left = MAX_ATTEMPTS
    session.identity_check = IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
    session.stage = "login"
    refresh_ui()


def _dismiss_reject_consent_dialog(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.show_reject_consent_dialog = False
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


def _owl_avatar_markup(tone: str, size: str) -> str:
    return f"""
    <div class="owl-avatar owl-avatar--{tone} owl-avatar--{size}" role="img" aria-label="Eulen-Avatar">
        <svg class="owl-avatar__svg" viewBox="0 0 120 120" aria-hidden="true" focusable="false">
            <path class="owl-avatar__coat" d="M31 103 C36 86 47 77 60 77 C73 77 84 86 89 103 Z" />
            <path class="owl-avatar__coat-line" d="M60 82 L60 103" />
            <circle class="owl-avatar__badge" cx="76" cy="93" r="7" />
            <path class="owl-avatar__badge-cross" d="M76 89.5 L76 96.5 M72.5 93 L79.5 93" />

            <g class="owl-avatar__head">
                <path class="owl-avatar__tufts" d="M28 43 C27 29 35 19 44 33 C49 30 54 28 60 28 C66 28 71 30 76 33 C85 19 93 29 92 43 C98 50 101 59 100 68 C98 88 81 100 60 100 C39 100 22 88 20 68 C19 59 22 50 28 43 Z" />
                <ellipse class="owl-avatar__face" cx="60" cy="62" rx="38" ry="39" />
                <path class="owl-avatar__wing owl-avatar__wing-left" d="M31 66 C33 80 40 88 50 92 C43 74 43 61 49 49 C39 50 33 56 31 66 Z" />
                <path class="owl-avatar__wing owl-avatar__wing-right" d="M89 66 C87 80 80 88 70 92 C77 74 77 61 71 49 C81 50 87 56 89 66 Z" />
                <path class="owl-avatar__chest" d="M43 78 C48 88 53 93 60 93 C67 93 72 88 77 78 C73 83 67 85 60 85 C53 85 47 83 43 78 Z" />

                <ellipse class="owl-avatar__mask owl-avatar__mask-left" cx="47" cy="56" rx="18" ry="20" />
                <ellipse class="owl-avatar__mask owl-avatar__mask-right" cx="73" cy="56" rx="18" ry="20" />

                <path class="owl-avatar__brow owl-avatar__brow-left" d="M37 43 C42 40 49 40 54 43" />
                <path class="owl-avatar__brow owl-avatar__brow-right" d="M66 43 C71 40 78 40 83 43" />

                <circle class="owl-avatar__eye-white" cx="47" cy="56" r="10.5" />
                <circle class="owl-avatar__eye-white" cx="73" cy="56" r="10.5" />
                <circle class="owl-avatar__pupil owl-avatar__pupil-left" cx="48" cy="57" r="4.5" />
                <circle class="owl-avatar__pupil owl-avatar__pupil-right" cx="72" cy="57" r="4.5" />
                <circle class="owl-avatar__catchlight" cx="50" cy="54" r="1.6" />
                <circle class="owl-avatar__catchlight" cx="74" cy="54" r="1.6" />
                <ellipse class="owl-avatar__lid owl-avatar__lid-left" cx="47" cy="56" rx="11" ry="10" />
                <ellipse class="owl-avatar__lid owl-avatar__lid-right" cx="73" cy="56" rx="11" ry="10" />

                <path class="owl-avatar__beak owl-avatar__beak-closed" d="M55 66 L60 73 L65 66 Z" />
                <ellipse class="owl-avatar__mouth-inside" cx="60" cy="72" rx="5.6" ry="4.8" />
                <path class="owl-avatar__beak owl-avatar__beak-open" d="M53 66 C55 76 65 76 67 66 C64 70 56 70 53 66 Z" />
                <path class="owl-avatar__beak owl-avatar__beak-wide" d="M50 65 C53 82 67 82 70 65 C66 71 54 71 50 65 Z" />
                <path class="owl-avatar__smile" d="M51 75 C56 80 64 80 69 75" />
            </g>

            <circle class="owl-avatar__thought-dot owl-avatar__thought-dot-one" cx="88" cy="33" r="3.8" />
            <circle class="owl-avatar__thought-dot owl-avatar__thought-dot-two" cx="96" cy="25" r="2.6" />
        </svg>
    </div>
    """


def _render_owl_avatar(tone: str, size: str = "large") -> None:
    ui.html(_owl_avatar_markup(tone, size)).classes("shrink-0")


def _get_avatar_state(session: BrowserSession) -> dict[str, str]:
    ctrl = session.primary_controller
    if ctrl is None:
        return {
            "icon": "sentiment_satisfied",
            "tone": "calm",
            "title": "Eulen-Assistent",
            "subtitle": "Bereit für die Voranamnese.",
        }

    if ctrl.state == DialogueState.REQUEST_CONSENT:
        return {
            "icon": "waving_hand",
            "tone": "calm",
            "title": "Eulen-Assistent",
            "subtitle": "Ich erkläre Ihnen kurz den Ablauf.",
        }

    if ctrl.state == DialogueState.ANAMNESIS:
        if session.anamnesis_mode == "guided":
            return {
                "icon": "record_voice_over",
                "tone": "listening",
                "title": "Eulen-Assistent",
                "subtitle": "Ich stelle Ihnen die Anamnese-Fragen nacheinander.",
            }
        return {
            "icon": "forum",
            "tone": "thinking",
            "title": "Eulen-Assistent",
            "subtitle": "Sie können Formular oder geführtes Gespräch wählen.",
        }

    if ctrl.state in (DialogueState.RED_FLAG_CHECK, DialogueState.ESCALATION):
        return {
            "icon": "priority_high",
            "tone": "alert",
            "title": "Eulen-Assistent",
            "subtitle": "Ich achte auf Warnzeichen und informiere das Team.",
        }

    if ctrl.state in (DialogueState.SUMMARY, DialogueState.HANDOVER, DialogueState.END):
        return {
            "icon": "sentiment_very_satisfied",
            "tone": "done",
            "title": "Eulen-Assistent",
            "subtitle": "Die Angaben wurden strukturiert aufbereitet.",
        }

    return {
        "icon": "psychology_alt",
        "tone": "thinking",
        "title": "Eulen-Assistent",
        "subtitle": "Ich begleite Sie durch den Ablauf.",
    }


def _speak_text(text: str) -> None:
    escaped = (
        text.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
    )
    ui.run_javascript(
        f"""
        (() => {{
            const avatarClass = 'avatar-is-speaking';
            document.body.classList.remove(avatarClass);
            if (!('speechSynthesis' in window)) {{
                return;
            }}
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(`{escaped}`);
            utterance.lang = 'de-DE';
            utterance.rate = 0.95;
            utterance.pitch = 1.0;
            const voices = window.speechSynthesis.getVoices() || [];
            const germanVoice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('de'));
            if (germanVoice) {{
                utterance.voice = germanVoice;
            }}
            const stopSpeaking = () => document.body.classList.remove(avatarClass);
            utterance.onstart = () => document.body.classList.add(avatarClass);
            utterance.onend = stopSpeaking;
            utterance.onerror = stopSpeaking;
            window.speechSynthesis.speak(utterance);
        }})()
        """
    )


def _maybe_speak_latest_message(session: BrowserSession) -> None:
    if not session.speech_enabled or session.anamnesis_mode != "guided":
        return
    if session.spoken_message_count >= len(session.messages):
        return

    latest_entry = session.messages[-1] if session.messages else None
    if latest_entry is None or latest_entry.role != "system" or not latest_entry.text.strip():
        session.spoken_message_count = len(session.messages)
        return

    session.spoken_message_count = len(session.messages)
    _speak_text(latest_entry.text.strip())


def _render_guided_dialogue(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    _maybe_speak_latest_message(session)

    with ui.scroll_area().classes("chat-shell w-full rounded-3xl bg-white/45 p-4"):
        with ui.column().classes("w-full gap-3"):
            for entry in session.messages:
                _render_message(entry)

    ui.run_javascript("""
    setTimeout(() => {
        document.querySelectorAll('.chat-shell').forEach((shell) => {
            const container = shell.querySelector('.q-scrollarea__container') || shell;
            container.scrollTop = container.scrollHeight;
        });
    }, 0);
    """)

    ctrl = session.primary_controller
    current_q = ctrl.current_question if ctrl is not None else None
    is_yes_no = current_q is not None and current_q.input_type == "ja_nein"

    with ui.row().classes("w-full items-center justify-between gap-3 mb-3 flex-wrap"):
        ui.label("Der Assistent kann die Fragen vorlesen.").classes(
            "text-sm text-slate-600"
        )
        ui.button(
            "Stimme aus" if session.speech_enabled else "Stimme an",
            on_click=lambda: _toggle_speech(session, refresh_ui),
            icon="volume_off" if session.speech_enabled else "volume_up",
        ).props("outline").classes(
            "border-[var(--app-accent)] text-[var(--app-accent)]"
        )

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
            session.show_cancel_dialog = True
            refresh_ui()

        with ui.row().classes("w-full justify-center mt-2"):
            ui.button(
                "Abbrechen", on_click=cancel_yes_no
            ).props("outline dense").classes(
                "text-xs border-[rgba(159,29,32,0.25)] text-[#9f1d20]"
            )
        return

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
        session.show_cancel_dialog = True
        refresh_ui()

    answer_input = ui.input("Ihre Antwort").props("outlined").classes("w-full")
    answer_input.on("keydown.enter", lambda _: submit_answer())
    _render_speech_input_controls(answer_input.id)

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


def main_page(
    entry_mode: str = PATIENT_MODE,
    page_title: str = PAGE_TITLE,
) -> None:
    ui.colors(
        primary="#0f766e",
        secondary="#fff0db",
        accent="#17342f",
        positive="#17603d",
        negative="#9f1d20",
        warning="#b55a07",
    )
    ui.add_head_html(STYLE_BLOCK)

    session = BrowserSession(
        entry_mode=entry_mode,
        stage="staff_selection" if entry_mode == PERSONAL_MODE else "login",
    )

    def refresh_ui() -> None:
        render_header.refresh()
        render_main.refresh()
        render_sidebar.refresh()

    with ui.column().classes("app-shell gap-6"):
        @ui.refreshable
        def render_header() -> None:
            with ui.column().classes("gap-2"):
                ui.label("SET Semesterprojekt").classes("eyebrow")
                ui.label(page_title).classes("hero-title text-4xl font-bold")
                with ui.row().classes("gap-2 flex-wrap"):
                    for label, status in _get_process_steps(session):
                        ui.label(label).classes(f"status-chip status-chip--{status}")

        render_header()

        with ui.row().classes("w-full items-start gap-6 flex-wrap lg:flex-nowrap"):
            with ui.column().classes("min-w-0 grow gap-6"):
                @ui.refreshable
                def render_main() -> None:
                    if session.stage == "staff_selection":
                        _render_staff_selection(session, refresh_ui)
                    elif session.stage == "login":
                        _render_login(session, refresh_ui)
                    elif session.stage == "scenario":
                        _render_scenario_selection(session, refresh_ui)
                    elif session.editing_answers:
                        _render_answer_editor(session, refresh_ui)
                    else:
                        _render_dialogue(session, refresh_ui)

                    _render_cancel_overlay(session, refresh_ui)
                    _render_login_blocked_overlay(session, refresh_ui)
                    _render_reject_consent_overlay(session, refresh_ui)

                render_main()

            with ui.column().classes("w-full gap-6 lg:max-w-[340px]"):
                @ui.refreshable
                def render_sidebar() -> None:
                    _render_sidebar(session, refresh_ui)

                render_sidebar()

def _render_login(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        if session.is_personal_mode and session.current_patient is not None:
            ui.label("Patientenbestaetigung").classes("text-2xl font-semibold")
            ui.label(
                "Das Praxispersonal hat Sie bereits aus der Tagesliste ausgewählt. "
                "Bitte bestätigen Sie jetzt Name und Geburtsdatum, damit die vorbereiteten Szenarien starten können."
            ).classes("max-w-3xl text-[1rem] leading-7 text-slate-600")
            _render_summary_section(
                "Vorbereitung durch Praxispersonal",
                {
                    "Patient": _format_patient_name(session.current_patient),
                    "Geburtsdatum": _format_display_date(
                        session.current_patient.date_of_birth
                    ),
                    "Szenarien": " + ".join(
                        _get_scenario_title(key) for key in session.selected_scenarios
                    )
                    or "keine Auswahl",
                },
            )
        else:
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
                if session.is_personal_mode and session.selected_scenarios:
                    _start_scenarios(session, session.selected_scenarios, refresh_ui)
                    return
                session.stage = "scenario"
            elif result.escalate:
                session.login_blocked_until = time.time() + 15
                session.identity_check = session.identity_check.__class__(
                    session.identity_check.patients,
                    max_attempts=session.identity_check.max_attempts,
                )
            refresh_ui()

        with ui.row().classes("w-full justify-end gap-3"):
            if session.is_personal_mode:
                ui.button(
                    "Zur Personal-Auswahl",
                    on_click=lambda: _back_to_staff_selection(session, refresh_ui),
                ).props("outline")
            else:
                ui.button("Zurücksetzen", on_click=lambda: (session.reset(), refresh_ui())).props(
                    "outline"
                )
            ui.button("Anmelden", on_click=submit_login).props("unelevated").classes(
                "bg-[#0f766e] text-white"
            )


def _get_recommended_scenario_key(
    session: BrowserSession,
) -> str | None:
    if session.current_patient is None:
        return None
    return DialogueController.get_recommended_scenario(session.current_patient)


def _back_to_staff_selection(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.stage = "staff_selection"
    session.identity_check = IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
    session.attempts_left = MAX_ATTEMPTS
    session.login_message = ""
    session.login_tone = "tone-info"
    session.current_patient = None
    session.selected_scenarios.clear()
    refresh_ui()


SCENARIO_KEY_TO_UI: dict[str, str] = {
    "cough": "A",
    "chest_pain": "B",
    "hypertension": "C",
    "diabetes": "D",
}


def _get_recommended_scenario_ui_key(patient: PatientRecord | None) -> str | None:
    if patient is None:
        return None
    recommended = DialogueController.get_recommended_scenario(patient)
    return SCENARIO_KEY_TO_UI.get(recommended) if recommended else None


def _get_scenario_title(ui_key: str) -> str:
    for s in SCENARIOS:
        if s["key"] == ui_key:
            return f"Szenario {ui_key} – {s['title']}"
    return ui_key


def _render_scenario_selection(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    recommended = _get_recommended_scenario_key(session)
    recommended_ui_key = SCENARIO_KEY_TO_UI.get(recommended) if recommended else None

    selected: set[str] = set()

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        ui.label("Szenarien auswählen").classes("text-2xl font-semibold")

        if recommended_ui_key:
            ui.label(
                "Basierend auf Ihren Vorerkrankungen wird Szenario %s (%s) empfohlen."
                % (recommended_ui_key, next(s["title"] for s in SCENARIOS if s["key"] == recommended_ui_key))
            ).classes("tone-success status-chip w-fit")

        with ui.row().classes("w-full gap-4 flex-wrap"):
            for scenario in SCENARIOS:
                is_recommended = scenario["key"] == recommended_ui_key
                card_classes = (
                    "surface-card scenario-card min-w-[240px] grow shadow-none"
                )
                if is_recommended:
                    card_classes += " border-[3px] border-[#17603d] bg-[#e3f5e9]"

                with ui.card().classes(card_classes):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon(scenario["icon"]).classes(
                            f"rounded-2xl p-3 text-2xl {scenario['tone']}"
                        )
                        with ui.column().classes("gap-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(f"Szenario {scenario['key']}").classes("eyebrow")
                                if is_recommended:
                                    ui.label("Empfohlen").classes(
                                        "status-chip tone-success text-[0.7rem]"
                                    )
                            ui.label(scenario["title"]).classes("text-lg font-semibold")
                            ui.label(scenario["subtitle"]).classes(
                                "text-sm font-medium text-slate-500"
                            )
                    ui.label(scenario["description"]).classes(
                        "text-[0.95rem] leading-6 text-slate-600"
                    )
                    cb = ui.checkbox("Dieses Szenario auswählen")
                    cb.on("update:model-value", lambda e, key=scenario["key"], cb=cb: (
                        selected.add(key) if e.args else selected.discard(key)
                    ))

        ui.button(
            "Ausgewählte Szenarien starten",
            on_click=lambda: _start_scenarios(session, list(selected), refresh_ui),
        ).props("unelevated").classes("bg-[#0f766e] text-white mt-4 w-full")

        if recommended_ui_key:
            ui.button(
                "Nur empfohlenes Szenario starten",
                on_click=lambda: _start_scenarios(session, [recommended], refresh_ui),
            ).props("outline").classes("mt-2 w-full")


def _select_patient_for_personal_mode(
    session: BrowserSession, patient: PatientRecord, refresh_ui: Callable[[], None]
) -> None:
    previous_id = session.current_patient.patient_id if session.current_patient else None
    session.current_patient = patient
    if previous_id != patient.patient_id:
        recommended_ui_key = _get_recommended_scenario_ui_key(patient)
        session.selected_scenarios = [recommended_ui_key] if recommended_ui_key else []
    session.login_message = ""
    session.login_tone = "tone-info"
    refresh_ui()


def _toggle_staff_scenario(
    session: BrowserSession, scenario_key: str, is_selected: bool
) -> None:
    selected = set(session.selected_scenarios)
    if is_selected:
        selected.add(scenario_key)
    else:
        selected.discard(scenario_key)
    session.selected_scenarios = sorted(selected)


def _render_patient_detail_section(title: str, values: list[str] | tuple[str, ...]) -> None:
    if not values:
        return
    with ui.card().classes("surface-card w-full shadow-none"):
        ui.label(title).classes("text-base font-semibold")
        for value in values:
            ui.label(value).classes("whitespace-pre-wrap text-sm leading-6 text-slate-600")


def _render_selected_patient_preview(patient: PatientRecord) -> None:
    details = patient.details
    with ui.column().classes("w-full gap-4"):
        _render_summary_section(
            "Kurzübersicht",
            {
                "Patient": _format_patient_name(patient),
                "Geburtsdatum": _format_display_date(patient.date_of_birth),
                "Geschlecht": _format_detail_value(details.gender),
                "Status": _format_detail_value(details.status),
                "Wohnort": _format_detail_value(details.contact_city),
                "Versicherung": _format_detail_value(details.insurance),
                "Nächster Termin": _format_next_appointment(patient),
            },
        )
        _render_summary_section(
            "Kurzinfos",
            {
                "Dauerdiagnosen": _summarize_values(details.long_term_diagnoses),
                "Medikation": _summarize_values(patient.medications),
                "Risikofaktoren": _summarize_values(details.risk_factors),
                "Allergien": _summarize_values(details.allergies),
            },
        )
        if details.next_appointment_note:
            _render_summary_section("Terminhinweis", {"Hinweis": details.next_appointment_note})
        _render_patient_detail_section("Dauerdiagnosen", details.long_term_diagnoses)
        _render_patient_detail_section("Akutdiagnosen", details.acute_diagnoses)
        _render_patient_detail_section("Medikationsdetails", details.medication_details)
        _render_patient_detail_section("Risikofaktoren", details.risk_factors)
        _render_patient_detail_section("Patientenhinweise", details.patient_notes)
        _render_patient_detail_section("Offene Aufgaben", details.open_tasks)


def _handoff_to_patient(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    if session.current_patient is None:
        ui.notify("Bitte wählen Sie zuerst einen Patienten aus.", color="warning")
        return
    if not session.selected_scenarios:
        ui.notify("Bitte wählen Sie mindestens ein Szenario aus.", color="warning")
        return

    _start_scenarios(session, session.selected_scenarios, refresh_ui)


def _generate_patient_id() -> str:
    existing = [p.patient_id for p in PATIENTS if p.patient_id.startswith("MAN-")]
    numbers = []
    for pid in existing:
        try:
            numbers.append(int(pid.removeprefix("MAN-")))
        except ValueError:
            pass
    next_num = max(numbers) + 1 if numbers else 1
    return f"MAN-{next_num:04d}"


def _open_new_patient_dialog(
    session: BrowserSession,
    refresh_ui: Callable[[], None],
    edit_patient: PatientRecord | None = None,
) -> None:
    dialog = ui.dialog()
    dialog_style = "w-[540px] max-w-full p-6"
    with dialog, ui.card().classes(dialog_style):
        title = "Patient bearbeiten" if edit_patient else "Neuen Patienten anlegen"
        ui.label(title).classes("text-xl font-semibold mb-4")
        ui.label("Alle Felder sind optional.").classes("text-sm text-slate-500 mb-2")

        vorname = ui.input("Vorname").props("outlined").classes("w-full")
        nachname = ui.input("Nachname").props("outlined").classes("w-full")
        geburtsdatum = ui.input("Geburtsdatum").props("outlined type=date").classes("w-full")
        telefon = ui.input("Telefon").props("outlined").classes("w-full")

        if edit_patient:
            with ui.row().classes("w-full gap-3"):
                with ui.column().classes("grow gap-0"):
                    geschlecht = ui.select(
                        ["", "männlich", "weiblich", "divers"],
                        label="Geschlecht",
                        value=edit_patient.details.gender,
                    ).props("outlined").classes("w-full")
                with ui.column().classes("grow gap-0"):
                    groesse = ui.input(
                        "Größe (cm)",
                        value=str(edit_patient.details.groesse_cm or ""),
                    ).props("outlined type=number").classes("w-full")
            sprache = ui.input(
                "Sprache",
                value=edit_patient.details.language,
            ).props("outlined").classes("w-full")
            wohnort = ui.input(
                "Wohnort",
                value=edit_patient.details.contact_city,
            ).props("outlined").classes("w-full")
            versicherung = ui.input(
                "Versicherung",
                value=edit_patient.details.insurance,
            ).props("outlined").classes("w-full")
        else:
            geschlecht = None  # type: ignore[assignment]
            groesse = None
            sprache = None
            wohnort = None
            versicherung = None

        notizen = ui.textarea("Notizen").props("outlined").classes("w-full")

        if edit_patient:
            vorname.value = edit_patient.first_name
            nachname.value = edit_patient.last_name
            geburtsdatum.value = edit_patient.date_of_birth
            telefon.value = edit_patient.details.phone
            notizen.value = edit_patient.details.notes

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Abbrechen", on_click=dialog.close).props("outline")

            def save() -> None:
                pid = edit_patient.patient_id if edit_patient else _generate_patient_id()

                orig_details = edit_patient.details if edit_patient else PatientDetails()
                details = PatientDetails(
                    phone=telefon.value or orig_details.phone,
                    notes=notizen.value or orig_details.notes,
                    gender=geschlecht.value if geschlecht is not None else orig_details.gender,
                    language=sprache.value if sprache is not None else orig_details.language,
                    contact_city=wohnort.value if wohnort is not None else orig_details.contact_city,
                    insurance=versicherung.value if versicherung is not None else orig_details.insurance,
                    groesse_cm=int(groesse.value) if groesse is not None and groesse.value.strip() else orig_details.groesse_cm,
                    next_appointment_at=orig_details.next_appointment_at,
                    next_appointment_type=orig_details.next_appointment_type,
                    next_appointment_note=orig_details.next_appointment_note,
                    allergies=orig_details.allergies,
                    long_term_diagnoses=orig_details.long_term_diagnoses,
                    acute_diagnoses=orig_details.acute_diagnoses,
                    risk_factors=orig_details.risk_factors,
                    medication_details=orig_details.medication_details,
                    patient_notes=orig_details.patient_notes,
                    open_tasks=orig_details.open_tasks,
                    status=orig_details.status,
                )
                orig_first = edit_patient.first_name if edit_patient else vorname.value or ""
                orig_last = edit_patient.last_name if edit_patient else nachname.value or ""
                orig_dob = edit_patient.date_of_birth if edit_patient else geburtsdatum.value or ""
                orig_meds = edit_patient.medications if edit_patient else []
                orig_conds = edit_patient.conditions if edit_patient else ""
                patient = PatientRecord(
                    patient_id=pid,
                    first_name=vorname.value or orig_first,
                    last_name=nachname.value or orig_last,
                    date_of_birth=geburtsdatum.value or orig_dob,
                    medications=orig_meds,
                    conditions=orig_conds,
                    details=details,
                )

                client = PatientListClient(
                    Path("app/patient_import/patientenTagesliste.json")
                )
                client.append_patient(patient)
                global PATIENTS
                PATIENTS = client.load_patients()

                dialog.close()
                if not edit_patient:
                    session.current_patient = patient
                    session.selected_scenarios.clear()
                    session.staff_search_query = ""
                ui.notify(
                    f"Patient {pid} {'aktualisiert' if edit_patient else 'angelegt'}.",
                    color="positive",
                )
                refresh_ui()

            ui.button("Speichern", on_click=save).props("unelevated").classes(
                "bg-[#0f766e] text-white"
            )

    dialog.open()


def _render_staff_selection(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    selected_patient = session.current_patient
    recommended_ui_key = _get_recommended_scenario_ui_key(selected_patient)

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        ui.label("Praxispersonal: Tagesliste und Szenarien").classes("text-2xl font-semibold")
        ui.label(
            "Wählen Sie einen Patienten aus der Tagesliste aus und markieren Sie alle Szenarien, "
            "die für die assistierte Anamnese vorbereitet werden sollen. Danach startet direkt der Patientenmodus "
            "mit den vorbereiteten Szenarien, ohne erneute Anmeldung."
        ).classes("max-w-4xl text-[1rem] leading-7 text-slate-600")

        if selected_patient is None:
            @ui.refreshable
            def render_filtered_patient_list() -> None:
                filtered_patients = [
                    patient
                    for patient in PATIENTS
                    if _patient_matches_staff_search(patient, session.staff_search_query)
                ]

                ui.label(f"{len(filtered_patients)} Treffer in der Tagesliste").classes(
                    "text-sm text-slate-500"
                )

                with ui.column().classes("w-full gap-4"):
                    for patient in filtered_patients:
                        patient_recommendation = _get_recommended_scenario_ui_key(patient)
                        with ui.card().classes("surface-card scenario-card w-full shadow-none"):
                            with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
                                with ui.column().classes("gap-1"):
                                    ui.label(_format_patient_name(patient)).classes("text-lg font-semibold")
                                    ui.label(
                                        f"Geburtsdatum: {_format_display_date(patient.date_of_birth)}"
                                    ).classes("text-sm text-slate-500")
                                    ui.label(f"Patienten-ID: {patient.patient_id}").classes(
                                        "text-sm text-slate-500"
                                    )
                                with ui.column().classes("items-end gap-2"):
                                    if patient_recommendation:
                                        ui.label(
                                            f"Empfohlen: Szenario {patient_recommendation}"
                                        ).classes("status-chip tone-success")
                                    ui.button(
                                        "Auswählen",
                                        on_click=lambda patient=patient: _select_patient_for_personal_mode(
                                            session, patient, refresh_ui
                                        ),
                                    ).props("unelevated").classes("min-w-[130px]")

                            _render_summary_section(
                                "Kurzübersicht",
                                {
                                    "Dauerdiagnosen": _summarize_values(
                                        patient.details.long_term_diagnoses
                                    ),
                                    "Medikation": _summarize_values(patient.medications),
                                    "Risikofaktoren": _summarize_values(patient.details.risk_factors),
                                    "Nächster Termin": _format_next_appointment(patient),
                                },
                            )

                    if not filtered_patients:
                        with ui.card().classes("surface-card w-full shadow-none"):
                            ui.label("Kein Patient gefunden").classes("text-lg font-semibold")
                            ui.label(
                                "Bitte prüfen Sie Schreibweise oder Geburtsdatum und versuchen Sie es erneut."
                            ).classes("text-sm leading-6 text-slate-600")

            with ui.row().classes("w-full items-center gap-3"):
                search_input = ui.input(
                    "Patient suchen (Name, Geburtsdatum oder Patienten-ID)",
                    value=session.staff_search_query,
                ).props("outlined clearable").classes("grow")
                search_input.on(
                    "update:model-value",
                    lambda e: (
                        setattr(session, "staff_search_query", e.args or ""),
                        render_filtered_patient_list.refresh(),
                    ),
                )

                ui.button(
                    "Neuer Patient +",
                    on_click=lambda: _open_new_patient_dialog(session, refresh_ui),
                ).props("unelevated").classes("bg-[#17603d] text-white whitespace-nowrap")

            render_filtered_patient_list()
        else:
            with ui.row().classes("w-full justify-between items-center gap-3 flex-wrap"):
                ui.label("Ausgewählter Patient").classes("eyebrow")
                with ui.row().classes("items-center gap-2"):
                    ui.button(
                        "Bearbeiten",
                        on_click=lambda: _open_new_patient_dialog(
                            session, refresh_ui,
                            edit_patient=session.current_patient,
                        ),
                    ).props("outline")
                    ui.button(
                        "Zur Tagesliste zurück",
                        on_click=lambda: _back_to_staff_selection(session, refresh_ui),
                    ).props("outline")

            _render_selected_patient_preview(selected_patient)

            if recommended_ui_key:
                ui.label(
                    f"Automatisch vorausgewählt: Szenario {recommended_ui_key}"
                ).classes("status-chip tone-success w-fit")

            with ui.card().classes("surface-card w-full shadow-none"):
                ui.label("Szenarien festlegen").classes("text-lg font-semibold")
                ui.label(
                    "Mehrfachauswahl ist erlaubt. Die markierten Szenarien werden direkt im Patientenmodus gestartet."
                ).classes("text-sm leading-6 text-slate-600")

                with ui.column().classes("w-full gap-3 mt-3"):
                    for scenario in SCENARIOS:
                        is_recommended = scenario["key"] == recommended_ui_key
                        is_checked = scenario["key"] in set(session.selected_scenarios)
                        card_classes = "surface-card scenario-card w-full shadow-none"
                        if is_recommended:
                            card_classes += " border-[2px] border-[#17603d] bg-[#e3f5e9]"
                        with ui.card().classes(card_classes):
                            with ui.row().classes("items-start gap-3"):
                                ui.icon(scenario["icon"]).classes(
                                    f"rounded-2xl p-3 text-2xl {scenario['tone']}"
                                )
                                with ui.column().classes("grow gap-1"):
                                    with ui.row().classes("items-center gap-2 flex-wrap"):
                                        ui.label(f"Szenario {scenario['key']}").classes("eyebrow")
                                        if is_recommended:
                                            ui.label("Empfohlen").classes(
                                                "status-chip tone-success text-[0.7rem]"
                                            )
                                    ui.label(scenario["title"]).classes("text-lg font-semibold")
                                    ui.label(scenario["subtitle"]).classes(
                                        "text-sm font-medium text-slate-500"
                                    )
                                    ui.label(scenario["description"]).classes(
                                        "text-sm leading-6 text-slate-600"
                                    )
                                checkbox = ui.checkbox(
                                    "Für den Patienten vorbereiten",
                                    value=is_checked,
                                )
                                checkbox.on(
                                    "update:model-value",
                                    lambda e, key=scenario["key"]: _toggle_staff_scenario(
                                        session, key, bool(e.args)
                                    ),
                                )

            with ui.row().classes("w-full justify-end gap-3"):
                ui.button(
                    "Szenarien leeren",
                    on_click=lambda: (
                        setattr(session, "selected_scenarios", []),
                        refresh_ui(),
                    ),
                ).props("outline")
                ui.button(
                    "Patientenmodus starten",
                    on_click=lambda: _handoff_to_patient(session, refresh_ui),
                ).props("unelevated").classes("bg-[#0f766e] text-white")


def _start_scenarios(
    session: BrowserSession, scenario_keys: list[str], refresh_ui: Callable[[], None]
) -> None:
    if session.current_patient is None:
        ui.notify("Es ist kein Patient angemeldet.", color="negative")
        return
    if not scenario_keys:
        ui.notify("Bitte wählen Sie mindestens ein Szenario aus.", color="warning")
        return

    session.selected_scenarios = scenario_keys
    session.controller = None
    session.controllers.clear()
    session.messages.clear()
    session.pending_input = None
    session.simulated_bp = None
    session.simulated_weight = None
    session.simulated_oximeter = None
    session.avatar_messages.clear()
    session.chat_input_text = ""
    session.prefilled_answers.clear()
    session.chat_phase_done = False
    session.anamnesis_mode = None
    session.stage = "dialogue"

    for key in scenario_keys:
        ctrl = DialogueController(
            scenario_key=key,
            patient=session.current_patient,
            display_message=lambda text: _append_system_message(session, text),
            request_input=lambda callback: _request_dialogue_input(session, callback),
        )
        ctrl.start()
        session.controllers.append(ctrl)

    refresh_ui()


def _render_dialogue(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    ctrl = session.primary_controller
    if ctrl is None:
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
                ui.label(ctrl.phase_label).classes("eyebrow")
                if session.anamnesis_mode is not None:
                    ui.label("Assistierte Anamnese").classes("text-2xl font-semibold")

        if ctrl.state in (
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

        elif ctrl.state == DialogueState.ANAMNESIS:
            _render_mass_anamnesis(session, refresh_ui)

        else:
            _render_guided_dialogue(session, refresh_ui)

    if session.summary_ready:
        _render_summary(session, refresh_ui)


def _render_summary(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    ctrl = session.primary_controller
    if ctrl is None or ctrl.summary is None:
        return

    summary = ctrl.summary

    scenario_text = " + ".join(
        _get_scenario_title(k) for k in session.selected_scenarios
    )

    def _download_pdf() -> None:
        try:
            pdf_bytes = export_summary_pdf(ctrl.summary, session.current_patient)
            patient_id = session.current_patient.patient_id if session.current_patient else "unknown"
            ui.download(
                pdf_bytes,
                f"anamnese_{patient_id}.pdf",
            )
            ui.notify("PDF wird heruntergeladen.", color="positive")
        except Exception as exc:
            ui.notify(f"PDF-Fehler: {exc}", color="negative")

    def _render_summary_actions(sticky: bool = False) -> None:
        if sticky:
            with ui.card().classes("sticky-summary-actions w-full shadow-none"):
                with ui.row().classes("w-full justify-center gap-3 flex-wrap items-center p-3"):
                    ui.button(
                        "Antworten bearbeiten",
                        on_click=lambda: _start_editing(session, refresh_ui),
                    ).props("unelevated").classes("bg-[#0f766e] text-white min-w-[200px]")

                    ui.button(
                        "Als PDF exportieren",
                        on_click=_download_pdf,
                    ).props("outline").classes(
                        "border-[var(--app-accent)] text-[var(--app-accent)] min-w-[200px]"
                    )
            return

        with ui.row().classes("w-full justify-center gap-3 mt-6 flex-wrap"):
            ui.button(
                "Antworten bearbeiten",
                on_click=lambda: _start_editing(session, refresh_ui),
            ).props("unelevated").classes("bg-[#0f766e] text-white min-w-[200px]")

            ui.button(
                "Als PDF exportieren",
                on_click=_download_pdf,
            ).props("outline").classes(
                "border-[var(--app-accent)] text-[var(--app-accent)] min-w-[200px]"
            )

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
                    "Szenarien": scenario_text,
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

        _render_summary_actions(sticky=True)

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

        _render_summary_actions()


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
    prefilled: dict[str, str] | None = None,
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
            effective_answer = answer
            is_prefilled = False
            if prefilled and key in prefilled and prefilled[key]:
                effective_answer = prefilled[key]
                is_prefilled = True

            label = question.text
            if key in required_keys:
                label = f"{label} *"

            card_classes = "surface-card w-full shadow-none"
            if is_prefilled:
                card_classes += " border-l-4 border-l-[#17603d]"

            with ui.card().classes(card_classes) as card:
                containers[key] = card
                ui.label(label).classes(
                    "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
                )
                if is_prefilled:
                    ui.label("KI-Vorschlag").classes(
                        "text-[0.7rem] font-bold uppercase tracking-[0.1em] "
                        "text-[#17603d] bg-[#e3f5e9] px-2 py-0.5 rounded w-fit"
                    )

                if question.input_type == "ja_nein":
                    radio_value = None
                    if effective_answer in ("Ja", "Nein"):
                        radio_value = effective_answer
                    elif effective_answer.lower() in ("ja", "j", "yes", "y"):
                        radio_value = "Ja"
                    elif effective_answer.lower() in ("nein", "n", "no"):
                        radio_value = "Nein"
                    radio = ui.radio(
                        ["Ja", "Nein"],
                        value=radio_value,
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
                            init_val = float(effective_answer.replace(",", "."))
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
                            value=effective_answer,
                            placeholder="Zahl eingeben oder 'unbekannt'",
                        ).classes("w-full").props("outlined")
                        fields[key] = inp
                else:
                    ta = ui.textarea(
                        value=effective_answer,
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
    if not session.show_cancel_dialog or session.primary_controller is None:
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


def _do_reset_session(session: BrowserSession) -> None:
    session.controller = None
    session.controllers.clear()
    session.selected_scenarios.clear()
    session.messages.clear()
    session.pending_input = None
    session.anamnesis_mode = None
    session.chat_phase_done = False
    session.prefilled_answers.clear()
    session.stage = "staff_selection" if session.is_personal_mode else "scenario"


def _confirm_cancel_anamnesis(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.primary_controller is None:
        return
    session.show_cancel_dialog = False

    # Sprache sofort stoppen
    ui.run_javascript(
        "if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); } "
        "document.body.classList.remove('avatar-is-speaking');"
    )

    if session.anamnesis_mode == "guided":
        abschluss = "Die Anamnese wurde abgebrochen."
        escaped = (
            abschluss.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("${", "\\${")
        )
        ui.run_javascript(
            f"""
            const u = new SpeechSynthesisUtterance(`{escaped}`);
            u.lang = 'de-DE';
            u.rate = 0.95;
            window.speechSynthesis.speak(u);
            """
        )
        _do_reset_session(session)
        ui.timer(2.8, lambda: refresh_ui(), once=True)
        return

    _do_reset_session(session)
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


def _render_reject_consent_overlay(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if not session.show_reject_consent_dialog:
        return

    with ui.element("div").classes("fixed inset-0 bg-black/40 z-50"):
        with ui.card().classes(
            "surface-card shadow-none border-2 border-[#9f1d20]"
        ).style(
            "position: fixed; top: 50%; left: 50%; "
            "transform: translate(-50%, -50%); z-index: 51;"
        ):
            ui.label("Zustimmung verweigern").classes("text-lg font-semibold")
            ui.label(
                "Sind Sie sicher, dass Sie der Anamnese nicht zustimmen möchten?\n"
                "Ohne Ihre Zustimmung kann die Anamnese nicht durchgeführt werden.\n\n"
                "Bitte wenden Sie sich an das Praxispersonal."
            ).classes(
                "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
            )
            with ui.row().classes("w-full gap-3 justify-center mt-4"):
                ui.button(
                    "Ja, ablehnen",
                    on_click=lambda: _confirm_reject_consent(session, refresh_ui),
                ).props("unelevated").classes(
                    "bg-[#9f1d20] text-white min-w-[140px]"
                )
                ui.button(
                    "Nein, zurück",
                    on_click=lambda: _dismiss_reject_consent_dialog(session, refresh_ui),
                ).props("outline").classes(
                    "border-[rgba(159,29,32,0.25)] text-[#9f1d20] min-w-[140px]"
                )


def _render_avatar(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    avatar = _get_avatar_state(session)

    with ui.card().classes("surface-card w-full shadow-none avatar-container"):
        with ui.row().classes("avatar-panel w-full items-center gap-4"):
            _render_owl_avatar(avatar["tone"])
            with ui.column().classes("gap-1"):
                ui.label(avatar["title"]).classes("text-base font-semibold")
                ui.label(avatar["subtitle"]).classes(
                    "text-sm leading-6 text-slate-600"
                )

        if session.stage == "dialogue" and session.primary_controller is not None:
            ui.button(
                "Avatar begruessen",
                on_click=lambda: _on_avatar_click(),
            ).props("outline").classes("mt-4 w-full")


def _on_avatar_click() -> None:
    ui.notify(
        "Willkommen, ich begleite Sie durch die Anamnese.",
        color="info",
        position="bottom-right",
    )


def _toggle_speech(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    session.speech_enabled = not session.speech_enabled
    if not session.speech_enabled:
        ui.run_javascript(
            "if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); } "
            "document.body.classList.remove('avatar-is-speaking');"
        )
    else:
        session.spoken_message_count = 0
    refresh_ui()


def _render_speech_input_controls(target_input_id: str) -> None:
    with ui.row().classes("w-full items-center gap-3 mt-2"):
        mic_button = ui.button(icon="mic").props("round outline").classes(
            "text-[#0f766e]"
        )
        mic_status = ui.label(
            "Antwort alternativ per Spracheingabe ausfüllen."
        ).classes("text-xs text-slate-500")

    mic_recording = {"active": False}

    def _start_mic() -> None:
        ui.run_javascript(f"""
        (() => {{
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {{
                alert('Spracheingabe nicht unterstützt. Bitte Chrome oder Edge verwenden.');
                return;
            }}
            const r = new SR();
            r.lang = 'de-DE';
            r.continuous = true;
            r.interimResults = true;
            window._rec = r;
            window._recFinal = '';
            r.onresult = (e) => {{
                let interim = '';
                let finalText = '';
                for (let i = 0; i < e.results.length; i++) {{
                    if (e.results[i].isFinal) {{
                        finalText += e.results[i][0].transcript + ' ';
                    }} else {{
                        interim += e.results[i][0].transcript;
                    }}
                }}
                window._recFinal = finalText;
                const el = getElement({target_input_id});
                if (el) {{
                    el.inputValue = (finalText + interim).trim();
                }}
            }};
            r.onerror = () => {{ window._rec = null; }};
            r.onend = () => {{ window._rec = null; }};
            r.start();
        }})()
        """)
        mic_recording["active"] = True
        mic_status.set_text("Aufnahme läuft... Nochmal klicken zum Stoppen.")
        mic_button._props["icon"] = "stop"
        mic_button._props["color"] = "negative"
        mic_button.update()

    def _stop_mic() -> None:
        ui.run_javascript("if(window._rec){window._rec.stop();window._rec=null;}")
        mic_recording["active"] = False
        mic_status.set_text("Aufnahme beendet.")
        mic_button._props["icon"] = "mic"
        mic_button._props["color"] = None
        mic_button.update()

    def _toggle_mic() -> None:
        if mic_recording["active"]:
            _stop_mic()
        else:
            _start_mic()

    mic_button.on_click(_toggle_mic)


def _render_anamnesis_mode_choice(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        ui.label("Wie möchten Sie die Anamnese durchführen?").classes(
            "text-2xl font-semibold"
        )
        ui.label(
            "Sie können die Fragen klassisch als Formular beantworten oder sich vom Assistenten nacheinander durch die Anamnese führen lassen."
        ).classes("text-[1rem] leading-7 text-slate-600")

        with ui.row().classes("w-full gap-4 flex-wrap mt-2"):
            with ui.card().classes("surface-card grow min-w-[260px] shadow-none"):
                with ui.row().classes("items-center gap-3"):
                    _render_owl_avatar("listening", "small")
                    with ui.column().classes("gap-1"):
                        ui.label("Geführtes Gespräch").classes("text-lg font-semibold")
                        ui.label("Der Eulen-Avatar stellt die Anamnese-Fragen einzeln").classes(
                            "text-sm text-slate-500"
                        )
                ui.label(
                    "Der Button 'Bitte sprich mit mir' startet denselben Fragenkatalog wie unter 'Fragenformular', aber als Schritt-für-Schritt-Dialog."
                ).classes("mt-3 text-[0.95rem] leading-6 text-slate-600")
                ui.button(
                    "Bitte sprich mit mir",
                    on_click=lambda: (
                        setattr(session, "anamnesis_mode", "guided"),
                        setattr(session, "spoken_message_count", 0),
                        refresh_ui(),
                    ),
                ).props("unelevated").classes("mt-4 w-full bg-[#0f766e] text-white")

            with ui.card().classes("surface-card grow min-w-[260px] shadow-none"):
                with ui.row().classes("items-center gap-3"):
                    _render_owl_avatar("thinking", "small")
                    with ui.column().classes("gap-1"):
                        ui.label("Fragenformular").classes("text-lg font-semibold")
                        ui.label("Alle Fragen gesammelt auf einer Seite").classes(
                            "text-sm text-slate-500"
                        )
                ui.label(
                    "Gut, wenn alle Fragen auf einmal sichtbar sein sollen oder Angaben direkt vorausgefüllt und angepasst werden sollen."
                ).classes("mt-3 text-[0.95rem] leading-6 text-slate-600")
                ui.button(
                    "Formular verwenden",
                    on_click=lambda: (
                        setattr(session, "anamnesis_mode", "form"),
                        refresh_ui(),
                    ),
                ).props("outline").classes(
                    "mt-4 w-full border-[var(--app-accent)] text-[var(--app-accent)]"
                )


def _render_anamnesis_mode_toolbar(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.primary_controller is None or session.primary_controller.state != DialogueState.ANAMNESIS:
        return

    with ui.card().classes("surface-card w-full shadow-none"):
        ui.label("Anamnese-Modus").classes("eyebrow")
        ui.label("Sie können jederzeit zwischen Gespräch und Fragenformular wechseln.").classes(
            "text-sm leading-6 text-slate-600"
        )
        with ui.row().classes("w-full gap-3 flex-wrap mt-3"):
            ui.button(
                "Bitte sprich mit mir",
                on_click=lambda: (
                    setattr(session, "anamnesis_mode", "guided"),
                    setattr(session, "spoken_message_count", 0),
                    refresh_ui(),
                ),
            ).props("unelevated").classes("bg-[#0f766e] text-white")
            ui.button(
                "Formular verwenden",
                on_click=lambda: (
                    setattr(session, "anamnesis_mode", "form"),
                    refresh_ui(),
                ),
            ).props("outline").classes(
                "border-[var(--app-accent)] text-[var(--app-accent)]"
            )


def _render_symptom_chat(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    ctrl = session.primary_controller
    if ctrl is None:
        return

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        _render_anamnesis_mode_toolbar(session, refresh_ui)

        avatar = _get_avatar_state(session)

        with ui.row().classes("w-full items-center gap-4"):
            _render_owl_avatar(avatar["tone"], "medium")
            with ui.column().classes("gap-0"):
                ui.label(avatar["title"]).classes("text-sm font-semibold")
                ui.label("Vorab-Erfassung Ihrer Beschwerden").classes(
                    "text-xs text-slate-500"
                )

        with ui.element("div").classes("chat-bubble chat-bubble--system mt-4"):
            ui.label("Assistenzsystem").classes(
                "text-[0.74rem] font-bold uppercase tracking-[0.16em] opacity-75"
            )
            ui.label(
                "Bitte schildern Sie mir in Ihren eigenen Worten Ihre aktuellen "
                "Beschwerden und Symptome. Zum Beispiel: seit wann Sie die "
                "Beschwerden haben, was genau Sie spüren, ob Sie Fieber haben, "
                "welche Medikamente Sie nehmen usw.\n\n"
                "Ihre Angaben werden automatisch ausgewertet und der Fragebogen "
                "wird so weit wie möglich vorausgefüllt. Offene Fragen können "
                "Sie danach noch beantworten."
            ).classes("whitespace-pre-wrap text-[0.97rem] leading-7")

        symptom_input = ui.textarea(
            placeholder="Beschreiben Sie hier Ihre Beschwerden oder nutzen Sie das Mikrofon...",
            value=session.chat_input_text,
        ).classes("w-full mt-4 symptom-textarea").props("outlined rows=6")

        with ui.row().classes("w-full items-center gap-3 mt-2"):
            mic_button = ui.button(icon="mic").props("round outline").classes(
                "text-[#0f766e]"
            )
            mic_status = ui.label("").classes("text-xs text-slate-500")

        mic_recording = {"active": False}
        ta_id = symptom_input.id

        def _start_mic() -> None:
            ui.run_javascript(f"""
            (() => {{
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SR) {{ alert('Spracheingabe nicht unterstützt. Bitte Chrome oder Edge verwenden.'); return; }}
                const r = new SR();
                r.lang = 'de-DE';
                r.continuous = true;
                r.interimResults = true;
                window._rec = r;
                window._recFinal = '';
                r.onresult = (e) => {{
                    let interim = '';
                    let finalText = '';
                    for (let i = 0; i < e.results.length; i++) {{
                        if (e.results[i].isFinal) {{
                            finalText += e.results[i][0].transcript + ' ';
                        }} else {{
                            interim += e.results[i][0].transcript;
                        }}
                    }}
                    window._recFinal = finalText;
                    const el = getElement({ta_id});
                    if (el) {{
                        el.inputValue = (finalText + interim).trim();
                    }}
                }};
                r.onerror = (ev) => {{ console.log('Speech error:', ev.error); window._rec = null; }};
                r.onend = () => {{ window._rec = null; }};
                r.start();
            }})()
            """)
            mic_recording["active"] = True
            mic_status.set_text("Aufnahme läuft... Nochmal klicken zum Stoppen.")
            mic_button._props["icon"] = "stop"
            mic_button._props["color"] = "negative"
            mic_button.update()

        def _stop_mic() -> None:
            ui.run_javascript("if(window._rec){window._rec.stop();window._rec=null;}")
            mic_recording["active"] = False
            mic_status.set_text("Aufnahme beendet.")
            mic_button._props["icon"] = "mic"
            mic_button._props["color"] = None
            mic_button.update()

        def _toggle_mic() -> None:
            if mic_recording["active"]:
                _stop_mic()
            else:
                _start_mic()

        mic_button.on_click(_toggle_mic)

        def _on_submit_chat() -> None:
            text = (symptom_input.value or "").strip()
            session.chat_input_text = text

            if not text:
                ui.notify(
                    "Bitte beschreiben Sie Ihre Beschwerden oder klicken Sie auf 'Ueberspringen'.",
                    color="warning",
                )
                return

            questions = [q for q, _ in ctrl.get_questions_with_answers()]
            ui.notify("KI-Auswertung läuft...", color="info", position="top")
            prefilled = extract_answers(text, questions)
            session.prefilled_answers = prefilled
            session.chat_phase_done = True
            refresh_ui()

        def _on_skip() -> None:
            session.prefilled_answers = {}
            session.chat_phase_done = True
            refresh_ui()

        with ui.row().classes("w-full justify-end gap-3 mt-4"):
            ui.button(
                "Ueberspringen", on_click=_on_skip
            ).props("outline").classes(
                "border-[rgba(159,29,32,0.25)] text-[#9f1d20]"
            )
            ui.button(
                "Auswerten und weiter", on_click=_on_submit_chat
            ).props("unelevated").classes("bg-[#0f766e] text-white")


def _render_mass_anamnesis(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.controllers:
        _render_mass_anamnesis_multi(session, refresh_ui)
        return
    if session.primary_controller is not None:
        _render_mass_anamnesis_single(session, refresh_ui)


def _render_mass_anamnesis_single(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    ctrl = session.primary_controller
    if ctrl is None:
        return

    if session.anamnesis_mode == "guided":
        _render_guided_dialogue(session, refresh_ui)
        return

    if session.anamnesis_mode is None:
        _render_anamnesis_mode_choice(session, refresh_ui)
        return

    if not session.chat_phase_done:
        _render_symptom_chat(session, refresh_ui)
        return

    questions_with_answers = ctrl.get_questions_with_answers()

    _render_anamnesis_mode_toolbar(session, refresh_ui)

    def _on_submit(answers: dict[str, str]) -> None:
        try:
            ctrl.submit_mass_anamnesis(answers)
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    def _on_cancel() -> None:
        session.show_cancel_dialog = True
        refresh_ui()

    _build_question_form(
        controller=ctrl,
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
        prefilled=session.prefilled_answers,
    )


def _render_mass_anamnesis_multi(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    controllers = session.controllers
    if not controllers:
        return

    if session.anamnesis_mode == "guided":
        _render_guided_dialogue(session, refresh_ui)
        return

    if session.anamnesis_mode is None:
        _render_anamnesis_mode_choice(session, refresh_ui)
        return

    if not session.chat_phase_done:
        _render_symptom_chat(session, refresh_ui)
        return

    all_questions: list[tuple[DialogueController, DialogueQuestion, str]] = []
    key_to_controllers: dict[str, list[DialogueController]] = {}
    for ctrl in controllers:
        for q, answer in ctrl.get_questions_with_answers():
            all_questions.append((ctrl, q, answer))
            key_to_controllers.setdefault(q.key, []).append(ctrl)

    duplicate_keys = {key for key, ctrls in key_to_controllers.items() if len(ctrls) > 1}

    seen_keys: set[str] = set()
    merged: list[tuple[DialogueController, DialogueQuestion, str]] = []

    for ctrl, q, answer in all_questions:
        if q.key in duplicate_keys:
            if q.key not in seen_keys:
                seen_keys.add(q.key)
                merged.append((ctrl, q, answer))
        else:
            merged.append((ctrl, q, answer))

    qa_for_form = [(q, answer) for _, q, answer in merged]

    questions_with_answers = qa_for_form

    _render_anamnesis_mode_toolbar(session, refresh_ui)

    required_keys_all: set[str] = set()
    q_text_map: dict[str, str] = {}
    input_types: dict[str, str] = {}
    for ctrl, q, answer in merged:
        required_keys_all.add(q.key) if q.required else None
        q_text_map[q.key] = q.text
        input_types[q.key] = q.input_type

    def _on_submit(answers: dict[str, str]) -> None:
        try:
            for ctrl in controllers:
                ctrl.submit_mass_anamnesis(answers)
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    def _on_cancel() -> None:
        session.show_cancel_dialog = True
        refresh_ui()

    dedup_info = ""
    if duplicate_keys:
        key_labels = ", ".join(sorted(duplicate_keys))
        dedup_info = (
            f"Die Fragen {key_labels} werden in mehreren Szenarien verwendet "
            "und daher nur einmal angezeigt."
        )

    scenario_text = " + ".join(
        _get_scenario_title(k) for k in session.selected_scenarios
    )

    _build_question_form(
        controller=controllers[0],
        questions_with_answers=questions_with_answers,
        title=f"Anamnese — {scenario_text}",
        description=(
            f"Alle Fragen aus den ausgewählten Szenarien auf einen Blick. "
            f"Pflichtfelder sind mit * markiert. "
            f"Einige Fragen werden dynamisch ein- oder ausgeblendet."
            + (f"\n\n{dedup_info}" if dedup_info else "")
        ),
        submit_label="Absenden",
        submit_callback=_on_submit,
        cancel_callback=_on_cancel,
        live_visibility=True,
        prefilled=session.prefilled_answers,
    )


def _render_answer_editor(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    ctrl = session.primary_controller
    if ctrl is None:
        return

    questions_with_answers = ctrl.get_questions_with_answers()

    def _on_submit(answers: dict[str, str]) -> None:
        try:
            for c in session.controllers:
                c.update_answers_and_regenerate(answers)
            session.editing_answers = False
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    _build_question_form(
        controller=ctrl,
        questions_with_answers=questions_with_answers,
        title="Antworten bearbeiten",
        description=(
            "Alle Fragen auf einen Blick. Aenderungen werden nach dem Speichern "
            "in die Zusammenfassung übernommen."
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
    ctrl = session.primary_controller
    with ui.card().classes("surface-card w-full shadow-none"):
        ui.label("Sitzung").classes("eyebrow")
        ui.label(_format_patient_name(session.current_patient)).classes(
            "text-xl font-semibold"
        )


        if session.current_patient is not None:
            ui.label(f"Patienten-ID: {session.current_patient.patient_id}").classes(
                "text-sm text-slate-500"
            )
            if session.selected_scenarios:
                scenario_text = " + ".join(
                    _get_scenario_title(k) for k in session.selected_scenarios
                )
                ui.label(f"Szenarien: {scenario_text}").classes(
                    "text-sm text-slate-500"
                )

        if ctrl is not None:
            ui.label(f"Aktuelle Phase: {ctrl.phase_label}").classes(
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

    if ctrl is not None and ctrl.state.value >= DialogueState.ANAMNESIS.value:
        with ui.card().classes("surface-card w-full shadow-none"):
            ui.label("Gerätesimulatoren").classes("eyebrow")

            with ui.column().classes("w-full gap-1 mt-2"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Blutdruck").classes("text-sm font-semibold")
                    ui.button("Simulieren", icon="monitor_heart",
                              on_click=lambda: _simulate_bp(session, refresh_ui)
                              ).props("dense outline")
                if session.simulated_bp:
                    ui.label(
                        f"{session.simulated_bp['systolisch']}/{session.simulated_bp['diastolisch']} mmHg"
                    ).classes("text-sm text-slate-600 ml-2")

            with ui.column().classes("w-full gap-1"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Gewicht").classes("text-sm font-semibold")
                    ui.button("Simulieren",
                              on_click=lambda: _simulate_weight(session, refresh_ui)
                              ).props("dense outline")
                if session.simulated_weight:
                    ui.label(
                        f"{session.simulated_weight['gewicht']} kg "
                        f"(BMI: {session.simulated_weight['bmi']}, {session.simulated_weight['klasse']})"
                    ).classes("text-sm text-slate-600 ml-2")

            with ui.column().classes("w-full gap-1"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Pulsoximeter").classes("text-sm font-semibold")
                    ui.button("Simulieren",
                              on_click=lambda: _simulate_oximeter(session, refresh_ui)
                              ).props("dense outline")
                if session.simulated_oximeter:
                    ui.label(
                        f"SpO\u2082: {session.simulated_oximeter['spo2']}%, "
                        f"Puls: {session.simulated_oximeter['puls']} bpm"
                    ).classes("text-sm text-slate-600 ml-2")

    if ctrl is not None and ctrl.export_path is not None:
        with ui.card().classes("surface-card w-full shadow-none"):
            ui.label("Export").classes("eyebrow")
            ui.label(str(ctrl.export_path)).classes(
                "break-all text-sm leading-6 text-slate-600"
            )
            if ctrl.summary is not None:
                def _download_pdf_from_sidebar() -> None:
                    try:
                        pdf_bytes = export_summary_pdf(ctrl.summary, session.current_patient)
                        patient_id = session.current_patient.patient_id if session.current_patient else "unknown"
                        ui.download(
                            pdf_bytes,
                            f"anamnese_{patient_id}.pdf",
                        )
                        ui.notify("PDF wird heruntergeladen.", color="positive")
                    except Exception as exc:
                        ui.notify(f"PDF-Fehler: {exc}", color="negative")

                with ui.column().classes("w-full gap-3 mt-3"):
                    ui.button(
                        "Antworten bearbeiten",
                        on_click=lambda: _start_editing(session, refresh_ui),
                    ).props("unelevated").classes("w-full bg-[#0f766e] text-white")
                    ui.button(
                        "Als PDF exportieren",
                        on_click=_download_pdf_from_sidebar,
                    ).props("outline").classes(
                        "w-full border-[var(--app-accent)] text-[var(--app-accent)]"
                    )

def _calculate_age(birth_date_str: str) -> int:
    if not birth_date_str:
        return 38
    try:
        born = date.fromisoformat(birth_date_str)
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except ValueError:
        return 38


def _simulate_bp(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    if session.current_patient is None:
        return
    p = session.current_patient
    sim = Simulator(
        geschlecht=p.details.gender,
        groesse_cm=p.details.groesse_cm,
        alter=_calculate_age(p.date_of_birth),
    )
    session.simulated_bp = sim.blutdruck()
    refresh_ui()


def _simulate_weight(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    if session.current_patient is None:
        return
    p = session.current_patient
    sim = Simulator(
        geschlecht=p.details.gender,
        groesse_cm=p.details.groesse_cm,
        alter=_calculate_age(p.date_of_birth),
    )
    session.simulated_weight = sim.gewicht()
    refresh_ui()


def _simulate_oximeter(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    if session.current_patient is None:
        return
    p = session.current_patient
    sim = Simulator(
        geschlecht=p.details.gender,
        groesse_cm=p.details.groesse_cm,
        alter=_calculate_age(p.date_of_birth),
    )
    session.simulated_oximeter = sim.pulsoximeter()
    refresh_ui()


def run_app(
    entry_mode: str = PATIENT_MODE,
    port: int = 8080,
    title: str = PAGE_TITLE,
) -> None:
    ui.run(
        root=lambda: main_page(
            entry_mode=entry_mode,
            page_title=title,
        ),
        host="127.0.0.1",
        port=port,
        title=title,
        reload=False,
        show=False,
    )
