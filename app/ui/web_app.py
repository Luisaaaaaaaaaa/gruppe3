from __future__ import annotations

import time
import json
from dataclasses import dataclass, field
from datetime import date, datetime

from app.devices.simulators import Simulator
from pathlib import Path
from typing import Callable

try:
    from nicegui import ui, run
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "NiceGUI ist nicht installiert. Bitte zuerst 'pip install -r requirements.txt' ausführen."
    ) from exc

from app.ai.symptom_extractor import extract_answers
from app.ai.assistant_chat import answer_question, OFFLINE_REPLY
from app.dialogue.consent_flow import (
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_QUESTION,
    ROLE_EXPLANATION,
)
from app.dialogue.dialogue_controller import DialogueController
from app.dialogue.state_machine import DialogueState
from app.identity.identity_check import IdentityCheck
from app.identity.name_normalization import normalize_person_name, person_name_key
from app.patient_import.patient_list_client import PatientListClient
from app.patient_import.patient_schema import PatientDetails, PatientRecord
from app.output.export_pdf import export_summary_pdf
from app.output.scenario_display import get_scenario_title

MAX_ATTEMPTS = 3
PAGE_TITLE = "KI-gestützter Anamnese-Agent"
PERSONAL_PAGE_TITLE = "SET Personalmodus"
PATIENT_MODE = "patient"
PERSONAL_MODE = "personal"
URL_PAGE_PARAM = "page"
URL_PATIENT_PARAM = "patient"
URL_SCENARIOS_PARAM = "scenarios"
URL_PAGE_STAFF = "staff"
URL_PAGE_LOGIN = "login"
URL_PAGE_SCENARIO = "scenario"
URL_PAGE_DIALOGUE = "dialogue"
URL_PAGE_EDIT = "edit"
URL_PAGES = {
    URL_PAGE_STAFF,
    URL_PAGE_LOGIN,
    URL_PAGE_SCENARIO,
    URL_PAGE_DIALOGUE,
    URL_PAGE_EDIT,
}
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
    reload_message: str = ""
    avatar_messages: list[ChatEntry] = field(default_factory=list)
    chat_input_text: str = ""
    assistant_messages: list[ChatEntry] = field(default_factory=list)
    assistant_input_text: str = ""
    prefilled_answers: dict[str, str] = field(default_factory=dict)
    draft_answers: dict[str, str] = field(default_factory=dict)
    guided_answer_message_keys: set[str] = field(default_factory=set)
    guided_answer_message_values: dict[str, str] = field(default_factory=dict)
    guided_answer_message_indices: dict[str, int] = field(default_factory=dict)
    ai_prefilled_keys: set[str] = field(default_factory=set)
    chat_phase_done: bool = False
    guided_started: bool = False
    anamnesis_mode: str | None = None
    speech_enabled: bool = True
    simulated_bp: dict | None = None
    simulated_weight: dict | None = None
    simulated_oximeter: dict | None = None
    spoken_message_count: int = 0
    staff_search_query: str = ""
    critical_confirmation_open: bool = False

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
        self.reload_message = ""
        self.avatar_messages.clear()
        self.chat_input_text = ""
        self.assistant_messages.clear()
        self.assistant_input_text = ""
        self.prefilled_answers.clear()
        self.draft_answers.clear()
        self.guided_answer_message_keys.clear()
        self.guided_answer_message_values.clear()
        self.guided_answer_message_indices.clear()
        self.ai_prefilled_keys.clear()
        self.chat_phase_done = False
        self.guided_started = False
        self.anamnesis_mode = None
        self.speech_enabled = True
        self.simulated_bp = None
        self.simulated_weight = None
        self.simulated_oximeter = None
        self.spoken_message_count = 0
        self.staff_search_query = ""
        self.critical_confirmation_open = False

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
    number_input: ui.number
    min_val: float
    max_val: float
    step: float
    info_label: ui.label | None = None
    value_recorded: bool = False

    @property
    def value(self) -> str:
        if self.unknown_checkbox.value:
            return "unbekannt"
        if not self.value_recorded:
            return ""
        value = self.number_input.value
        if value in (None, ""):
            return ""
        numeric_value = float(value)
        if self.step < 1:
            return f"{numeric_value:.1f}".rstrip("0").rstrip(".")
        return str(int(numeric_value))


@dataclass
class _DummyField:
    value: str = ""


@dataclass
class _BloodPressureField:
    sys_slider: ui.slider
    sys_input: ui.number
    dia_slider: ui.slider
    dia_input: ui.number
    unknown_checkbox: ui.checkbox
    value_recorded: bool = False

    @property
    def value(self) -> str:
        if self.unknown_checkbox.value:
            return "unbekannt"
        if not self.value_recorded:
            return ""
        if self.sys_input.value in (None, "") or self.dia_input.value in (None, ""):
            return ""
        return f"{int(float(self.sys_input.value))}/{int(float(self.dia_input.value))}"

    @property
    def sys_value(self) -> str:
        if self.unknown_checkbox.value:
            return "unbekannt"
        if not self.value_recorded:
            return ""
        if self.sys_input.value in (None, ""):
            return ""
        return str(int(float(self.sys_input.value)))

    @property
    def dia_value(self) -> str:
        if self.unknown_checkbox.value:
            return "unbekannt"
        if not self.value_recorded:
            return ""
        if self.dia_input.value in (None, ""):
            return ""
        return str(int(float(self.dia_input.value)))


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


def _normalize_url_page(value: object) -> str | None:
    page = str(value or "").strip().lower()
    return page if page in URL_PAGES else None


def _scenario_keys_from_value(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip().upper() for item in value]
    else:
        parts = [part.strip().upper() for part in str(value or "").split(",")]

    allowed = {scenario["key"] for scenario in SCENARIOS}
    result: list[str] = []
    for key in parts:
        if key in allowed and key not in result:
            result.append(key)
    return result


def _find_patient_by_id(patient_id: object) -> PatientRecord | None:
    normalized = str(patient_id or "").strip()
    if not normalized:
        return None
    for patient in PATIENTS:
        if patient.patient_id == normalized:
            return patient
    return None


def _request_url_state() -> dict[str, str]:
    try:
        params = ui.context.client.request.query_params
    except RuntimeError:
        return {}
    return {
        "page": params.get(URL_PAGE_PARAM, ""),
        "patient": params.get(URL_PATIENT_PARAM, ""),
        "scenarios": params.get(URL_SCENARIOS_PARAM, ""),
    }


def _session_url_page(session: BrowserSession) -> str:
    if session.editing_answers:
        return URL_PAGE_EDIT
    if session.stage == "staff_selection":
        return URL_PAGE_STAFF
    if session.stage == "login":
        return URL_PAGE_LOGIN
    if session.stage == "scenario":
        return URL_PAGE_SCENARIO
    return URL_PAGE_DIALOGUE


def _url_payload_for_session(session: BrowserSession) -> dict[str, object]:
    return {
        "page": _session_url_page(session),
        "patient": (
            session.current_patient.patient_id
            if session.current_patient is not None
            else ""
        ),
        "scenarios": list(session.selected_scenarios),
    }


def _sync_browser_url(session: BrowserSession) -> None:
    payload = _url_payload_for_session(session)
    ui.run_javascript(
        f"""
        (() => {{
            const payload = {json.dumps(payload)};
            const url = new URL(window.location.href);
            url.searchParams.set({json.dumps(URL_PAGE_PARAM)}, payload.page);
            if (payload.patient) {{
                url.searchParams.set({json.dumps(URL_PATIENT_PARAM)}, payload.patient);
            }} else {{
                url.searchParams.delete({json.dumps(URL_PATIENT_PARAM)});
            }}
            if (payload.scenarios.length > 0) {{
                url.searchParams.set({json.dumps(URL_SCENARIOS_PARAM)}, payload.scenarios.join(','));
            }} else {{
                url.searchParams.delete({json.dumps(URL_SCENARIOS_PARAM)});
            }}

            const state = {{...payload, appHistoryGuard: true}};
            window.__setAnamnesisCurrentHistory = () => {{
                window.__anamnesisCurrentHistory = {{state, href: url.href}};
                window.history.replaceState(state, '', url);
            }};
            window.__setAnamnesisCurrentHistory();

            if (!window.__anamnesisHistoryGuardInstalled) {{
                window.__anamnesisHistoryGuardInstalled = true;
                window.history.pushState(state, '', url);
                window.addEventListener('popstate', () => {{
                    const current = window.__anamnesisCurrentHistory;
                    if (!current) {{
                        return;
                    }}
                    window.history.pushState(current.state, '', current.href);
                    const now = Date.now();
                    if (now - (window.__anamnesisLastBackWarningAt || 0) < 1200) {{
                        return;
                    }}
                    window.__anamnesisLastBackWarningAt = now;
                    const message = 'Bitte nutzen Sie die Schaltflächen innerhalb der Anwendung. Die Zurück-Taste des Browsers ist hier deaktiviert.';
                    if (window.Quasar?.Notify) {{
                        window.Quasar.Notify.create({{
                            message,
                            color: 'warning',
                            position: 'top',
                            timeout: 3500,
                            multiLine: true,
                        }});
                    }} else {{
                        window.alert(message);
                    }}
                }});
            }}
        }})();
        """
    )


def _prepare_dialogue_session(
    session: BrowserSession, scenario_keys: list[str]
) -> None:
    if session.current_patient is None:
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
    session.assistant_messages.clear()
    session.assistant_input_text = ""
    session.prefilled_answers.clear()
    session.draft_answers.clear()
    session.guided_answer_message_keys.clear()
    session.guided_answer_message_values.clear()
    session.guided_answer_message_indices.clear()
    session.ai_prefilled_keys.clear()
    session.chat_phase_done = False
    session.guided_started = False
    session.anamnesis_mode = None
    session.editing_answers = False
    session.stage = "dialogue"

    for key in scenario_keys:
        ctrl = DialogueController(
            scenario_key=key,
            patient=session.current_patient,
            display_message=lambda text: _append_system_message(session, text),
            request_input=lambda callback: _request_dialogue_input(session, callback),
            # Fragen erst nach dem KI-Vorab-Chat stellen (auch im gefuehrten Modus).
            defer_anamnesis=True,
        )
        ctrl.start()
        session.controllers.append(ctrl)


def _initialize_session_from_url(session: BrowserSession) -> None:
    state = _request_url_state()
    page = _normalize_url_page(state.get("page"))
    patient = _find_patient_by_id(state.get("patient"))
    scenarios = _scenario_keys_from_value(state.get("scenarios"))

    if patient is not None:
        session.current_patient = patient
        session.selected_scenarios = scenarios

    if session.is_personal_mode:
        if page == URL_PAGE_LOGIN and patient is not None:
            session.stage = "login"
        else:
            session.stage = "staff_selection"
        return

    if page == URL_PAGE_SCENARIO and patient is not None:
        session.stage = "scenario"
        return

    if page in {URL_PAGE_DIALOGUE, URL_PAGE_EDIT} and patient is not None and scenarios:
        session.stage = "scenario"
        session.reload_message = "Der laufende Dialog wurde neu gestartet."
        return

    session.stage = "login"


def _format_patient_name(patient: PatientRecord | None) -> str:
    if patient is None:
        return "Noch kein Patient angemeldet"
    return normalize_person_name(f"{patient.first_name} {patient.last_name}")


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
    normalized_query = normalize_person_name(query).casefold()
    if not normalized_query:
        return True

    search_values = [
        _format_patient_name(patient),
        patient.date_of_birth,
        _format_display_date(patient.date_of_birth),
        patient.patient_id,
    ]
    combined = normalize_person_name(" ".join(search_values)).casefold()
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
        # Die Schleife fuehrt die vollstaendige Einwilligungs-Transition durch
        # (Bestaetigung anzeigen -> in den ANAMNESIS-Zustand wechseln). Der
        # Zustand ist danach aufgeschoben (defer_anamnesis) und wartet auf den
        # KI-Vorab-Chat. Den Einwilligungs-Callback NICHT zusaetzlich aufrufen,
        # sonst wuerde erneut weitergeschaltet und die Anamnese uebersprungen.
        for ctrl in session.controllers:
            if ctrl.state == DialogueState.REQUEST_CONSENT:
                ctrl._display(CONSENT_ACCEPTED)
                ctrl._state_machine.advance()
                ctrl._handle_state()

        session.pending_input = None
        session.messages.append(
            ChatEntry(role="user", text="Ja", tone="user")
        )
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
    session.guided_started = False
    session.prefilled_answers.clear()
    session.draft_answers.clear()
    session.guided_answer_message_keys.clear()
    session.guided_answer_message_values.clear()
    session.guided_answer_message_indices.clear()
    session.ai_prefilled_keys.clear()
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


def _remember_draft_answers(session: BrowserSession, answers: dict[str, str]) -> None:
    if not hasattr(session, "draft_answers"):
        session.draft_answers = {}
    for key, value in answers.items():
        session.draft_answers[key] = str(value).strip()


def _mark_guided_answer_message(
    session: BrowserSession,
    question_key: str,
    value: str,
    message_index: int | None = None,
) -> None:
    if not hasattr(session, "guided_answer_message_keys"):
        session.guided_answer_message_keys = set()
    if not hasattr(session, "guided_answer_message_values"):
        session.guided_answer_message_values = {}
    if not hasattr(session, "guided_answer_message_indices"):
        session.guided_answer_message_indices = {}
    session.guided_answer_message_keys.add(question_key)
    session.guided_answer_message_values[question_key] = _normalize_answer_for_chat(value)
    if message_index is not None:
        session.guided_answer_message_indices[question_key] = message_index


def _active_controllers(session: BrowserSession) -> list[DialogueController]:
    return session.controllers or (
        [session.controller] if session.controller is not None else []
    )


def _controller_answer_values(
    controllers: list[DialogueController],
) -> dict[str, str]:
    answers: dict[str, str] = {}
    for ctrl in controllers:
        for question, answer in ctrl.get_questions_with_answers():
            value = str(answer).strip()
            if value:
                answers[question.key] = value
    return answers


def _merged_anamnesis_answers(
    session: BrowserSession,
    controllers: list[DialogueController] | None = None,
) -> dict[str, str]:
    controllers = controllers if controllers is not None else _active_controllers(session)
    merged = _merged_prefilled_answers(session)
    merged.update(_controller_answer_values(controllers))
    merged.update(
        {
            key: str(value).strip()
            for key, value in getattr(session, "draft_answers", {}).items()
            if str(value).strip()
        }
    )
    return merged


def _normalize_answer_for_chat(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in ("ja", "j", "yes", "y"):
        return "Ja"
    if normalized in ("nein", "n", "no"):
        return "Nein"
    return value.strip()


def _insert_guided_messages(
    session: BrowserSession,
    index: int,
    entries: list[ChatEntry],
) -> None:
    if not entries:
        return
    if not hasattr(session, "guided_answer_message_indices"):
        session.guided_answer_message_indices = {}

    index = max(0, min(index, len(session.messages)))
    session.messages[index:index] = entries
    offset = len(entries)
    for key, answer_index in list(session.guided_answer_message_indices.items()):
        if answer_index >= index:
            session.guided_answer_message_indices[key] = answer_index + offset


def _find_pending_question_index(
    session: BrowserSession,
    question_text: str,
) -> int | None:
    for index in range(len(session.messages) - 1, -1, -1):
        entry = session.messages[index]
        if entry.role == "system" and entry.text.strip() == question_text.strip():
            return index
    return None


def _append_guided_answer_history(
    session: BrowserSession,
    controllers: list[DialogueController],
    answers: dict[str, str],
) -> None:
    if not hasattr(session, "guided_answer_message_keys"):
        session.guided_answer_message_keys = set()
    if not hasattr(session, "guided_answer_message_values"):
        session.guided_answer_message_values = {}
    if not hasattr(session, "guided_answer_message_indices"):
        session.guided_answer_message_indices = {}

    pending_index_by_key: dict[str, int] = {}
    for ctrl in controllers:
        current = getattr(ctrl, "current_question", None) if ctrl is not None else None
        if current is None:
            continue
        index = _find_pending_question_index(session, current.text)
        if index is None:
            continue
        pending_index_by_key[current.key] = index

    insertion_index = (
        min(pending_index_by_key.values())
        if pending_index_by_key
        else len(session.messages)
    )

    for ctrl in controllers:
        for question, _answer in ctrl.get_questions_with_answers():
            value = str(answers.get(question.key, "")).strip()
            if not value:
                continue
            display_value = _normalize_answer_for_chat(value)
            if session.guided_answer_message_values.get(question.key) == display_value:
                continue

            existing_index = session.guided_answer_message_indices.get(question.key)
            if existing_index is not None and existing_index < len(session.messages):
                existing_entry = session.messages[existing_index]
                if existing_entry.role == "user":
                    existing_entry.text = display_value
                    existing_entry.tone = "user"
                    session.guided_answer_message_values[question.key] = display_value
                    continue

            pending_index = pending_index_by_key.get(question.key)
            if pending_index is not None:
                _insert_guided_messages(
                    session,
                    pending_index + 1,
                    [ChatEntry(role="user", text=display_value, tone="user")],
                )
                session.guided_answer_message_keys.add(question.key)
                session.guided_answer_message_values[question.key] = display_value
                session.guided_answer_message_indices[question.key] = (
                    pending_index + 1
                )
                insertion_index = max(insertion_index, pending_index + 2)
                continue

            _insert_guided_messages(
                session,
                insertion_index,
                [
                    ChatEntry(role="system", text=question.text, tone="system"),
                    ChatEntry(role="user", text=display_value, tone="user"),
                ],
            )
            session.guided_answer_message_keys.add(question.key)
            session.guided_answer_message_values[question.key] = display_value
            session.guided_answer_message_indices[question.key] = insertion_index + 1
            insertion_index += 2


def _switch_anamnesis_mode(
    session: BrowserSession,
    mode: str,
    refresh_ui: Callable[[], None],
    answers: dict[str, str] | None = None,
) -> None:
    if answers is not None:
        _remember_draft_answers(session, answers)

    session.anamnesis_mode = mode

    if mode == "guided":
        session.spoken_message_count = 0
        controllers = _active_controllers(session)
        merged_answers = _merged_anamnesis_answers(session, controllers)
        _append_guided_answer_history(session, controllers, merged_answers)
        if session.guided_started:
            for ctrl in controllers:
                if ctrl.state == DialogueState.ANAMNESIS:
                    ctrl.apply_anamnesis_answers(
                        merged_answers,
                        continue_dialogue=True,
                    )

    refresh_ui()


def _answer_yes_no(
    session: BrowserSession, answer: str, refresh_ui: Callable[[], None]
) -> None:
    if session.pending_input is None:
        return

    ctrl = session.primary_controller
    current_q = ctrl.current_question if ctrl is not None else None
    if ctrl is not None and current_q is not None:
        if _check_live_form_escalation(
            session,
            [ctrl],
            {current_q.key: answer},
            refresh_ui,
        ):
            return

    session.messages.append(
        ChatEntry(role="user", text=answer, tone="user")
    )
    if current_q is not None:
        _remember_draft_answers(session, {current_q.key: answer})
        _mark_guided_answer_message(
            session,
            current_q.key,
            answer,
            len(session.messages) - 1,
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
        parsed_date = date(int(year), int(month), int(day))
    except ValueError as exc:
        raise ValueError("Bitte geben Sie ein gültiges Kalenderdatum ein.") from exc
    _validate_birth_date_not_in_future(parsed_date)
    return parsed_date


def _validate_birth_date_not_in_future(birth_date: date) -> None:
    if birth_date > date.today():
        raise ValueError("Das Geburtsdatum darf nicht in der Zukunft liegen.")


def _parse_optional_iso_birth_date(raw_value: str) -> str:
    normalized = raw_value.strip()
    if not normalized:
        return ""
    try:
        parsed_date = date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("Bitte geben Sie ein gueltiges Kalenderdatum ein.") from exc

    _validate_birth_date_not_in_future(parsed_date)
    return parsed_date.isoformat()


def _parse_required_iso_birth_date(raw_value: str) -> str:
    birth_date = _parse_optional_iso_birth_date(raw_value)
    if not birth_date:
        raise ValueError("Bitte geben Sie ein Geburtsdatum ein.")
    return birth_date


def _find_duplicate_patient(
    first_name: str,
    last_name: str,
    birth_date: str,
    exclude_patient_id: str | None = None,
) -> PatientRecord | None:
    first_key = person_name_key(first_name)
    last_key = person_name_key(last_name)
    return next(
        (
            patient
            for patient in PATIENTS
            if patient.patient_id != exclude_patient_id
            and person_name_key(patient.first_name) == first_key
            and person_name_key(patient.last_name) == last_key
            and patient.date_of_birth == birth_date
        ),
        None,
    )


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
    if session.critical_confirmation_open:
        return {
            "icon": "priority_high",
            "tone": "alert",
            "title": "Warnhinweis erkannt",
            "subtitle": "Bitte den kritischen Wert prüfen und das Praxisteam informieren.",
        }

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
            "title": "Warnhinweis erkannt",
            "subtitle": "Bitte sofort das Praxisteam informieren.",
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
        ctrl = session.primary_controller
        current_q = ctrl.current_question if ctrl is not None else None
        if ctrl is not None and current_q is not None:
            if _check_live_form_escalation(
                session,
                [ctrl],
                {current_q.key: answer},
                refresh_ui,
            ):
                return
        session.messages.append(
            ChatEntry(
                role="user",
                text=answer or "(keine Angabe)",
                tone="user",
            )
        )
        if current_q is not None:
            _remember_draft_answers(session, {current_q.key: answer})
            _mark_guided_answer_message(
                session,
                current_q.key,
                answer,
                len(session.messages) - 1,
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
    _initialize_session_from_url(session)

    def refresh_ui() -> None:
        render_header.refresh()
        render_main.refresh()
        render_sidebar.refresh()
        _sync_browser_url(session)

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

    ui.timer(0.1, lambda: _sync_browser_url(session), once=True)

def _render_login(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        max_birth_date = date.today().isoformat()
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

        birth_date_input = ui.input("Geburtsdatum").props(
            f"outlined type=date max={max_birth_date}"
        ).classes("w-full max-w-[260px]")

        def submit_login() -> None:
            normalized_first_name = normalize_person_name(first_name.value or "")
            normalized_last_name = normalize_person_name(last_name.value or "")

            if not normalized_first_name or not normalized_last_name:
                session.login_message = "Vorname und Nachname muessen ausgefuellt werden."
                session.login_tone = "tone-danger"
                refresh_ui()
                return

            try:
                birth_date = _parse_required_iso_birth_date(
                    birth_date_input.value or ""
                )
            except ValueError as exc:
                session.login_message = str(exc)
                session.login_tone = "tone-danger"
                refresh_ui()
                return

            result = session.identity_check.authenticate(
                normalized_first_name,
                normalized_last_name,
                birth_date,
            )
            session.login_message = result.message
            session.login_tone = "tone-success" if result.success else "tone-danger"
            session.attempts_left = result.attempts_left

            if result.success and result.patient is not None:
                _complete_successful_login(session, result.patient, refresh_ui)
                return
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
                ui.button("Zurücksetzen", on_click=lambda: _reset_browser_session(
                    session, refresh_ui
                )).props(
                    "outline"
                )
            ui.button("Anmelden", on_click=submit_login).props("unelevated").classes(
                "bg-[#0f766e] text-white"
            )


def _complete_successful_login(
    session: BrowserSession, patient: PatientRecord, refresh_ui: Callable[[], None]
) -> None:
    _dismiss_critical_warning()
    session.current_patient = patient
    session.attempts_left = MAX_ATTEMPTS
    session.login_message = ""
    session.login_tone = "tone-info"
    session.login_blocked_until = None
    session.reload_message = ""
    session.identity_check = IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
    if session.is_personal_mode and session.selected_scenarios:
        _start_scenarios(session, session.selected_scenarios, refresh_ui)
        return
    session.stage = "scenario"
    refresh_ui()


def _get_recommended_scenario_key(
    session: BrowserSession,
) -> str | None:
    if session.current_patient is None:
        return None
    return DialogueController.get_recommended_scenario(session.current_patient)


def _back_to_staff_selection(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    _dismiss_critical_warning()
    session.stage = "staff_selection"
    session.identity_check = IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
    session.attempts_left = MAX_ATTEMPTS
    session.login_message = ""
    session.login_tone = "tone-info"
    session.reload_message = ""
    session.current_patient = None
    session.selected_scenarios.clear()
    refresh_ui()


def _reset_browser_session(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    _dismiss_critical_warning()
    session.reset()
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
    scenario_title = get_scenario_title(ui_key)
    if scenario_title != str(ui_key or "").strip():
        return scenario_title
    for s in SCENARIOS:
        if s["key"] == ui_key:
            return f"Szenario {ui_key} – {s['title']}"
    return ui_key


def _render_scenario_selection(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    recommended = _get_recommended_scenario_key(session)
    recommended_ui_key = SCENARIO_KEY_TO_UI.get(recommended) if recommended else None

    patient = session.current_patient
    has_prepared = getattr(patient, "prepared_scenarios_saved", False) if patient else False
    prepared_keys = set(getattr(patient, "prepared_scenarios", ())) if has_prepared else set()

    selected: set[str] = set(session.selected_scenarios or prepared_keys)

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        ui.label("Szenarien auswählen").classes("text-2xl font-semibold")
        if session.reload_message:
            ui.label(session.reload_message).classes(
                "w-full rounded-2xl px-4 py-3 text-sm font-medium tone-warning"
            )

        if has_prepared and prepared_keys:
            titles = [_get_scenario_title(k) for k in sorted(prepared_keys)]
            ui.label(
                "Vom Praxispersonal vorbereitet: %s"
                % ", ".join(titles)
            ).classes("tone-success status-chip w-fit")
        elif recommended_ui_key:
            ui.label(
                "Basierend auf Ihren Vorerkrankungen wird Szenario %s (%s) empfohlen."
                % (recommended_ui_key, next(s["title"] for s in SCENARIOS if s["key"] == recommended_ui_key))
            ).classes("tone-success status-chip w-fit")

        with ui.row().classes("w-full gap-4 flex-wrap"):
            for scenario in SCENARIOS:
                is_prechecked = scenario["key"] in selected
                is_recommended = scenario["key"] == recommended_ui_key and not has_prepared
                card_classes = (
                    "surface-card scenario-card min-w-[240px] grow shadow-none"
                )
                if is_prechecked:
                    card_classes += " border-[3px] border-[#17603d] bg-[#e3f5e9]"

                with ui.card().classes(card_classes):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon(scenario["icon"]).classes(
                            f"rounded-2xl p-3 text-2xl {scenario['tone']}"
                        )
                        with ui.column().classes("gap-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(f"Szenario {scenario['key']}").classes("eyebrow")
                                if is_prechecked and has_prepared:
                                    ui.label("Vorbereitet").classes(
                                        "status-chip tone-success text-[0.7rem]"
                                    )
                                elif is_recommended:
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
                    cb = ui.checkbox("Dieses Szenario auswählen", value=is_prechecked)
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
    if previous_id != patient.patient_id:
        _dismiss_critical_warning()
    session.current_patient = patient
    if previous_id != patient.patient_id:
        if getattr(patient, "prepared_scenarios_saved", False):
            session.selected_scenarios = list(
                getattr(patient, "prepared_scenarios", ())
            )
        else:
            recommended_ui_key = _get_recommended_scenario_ui_key(patient)
            session.selected_scenarios = [recommended_ui_key] if recommended_ui_key else []
    session.login_message = ""
    session.login_tone = "tone-info"
    refresh_ui()


def _save_staff_scenarios(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    if session.current_patient is None:
        ui.notify("Kein Patient ausgewählt.", color="warning")
        return
    pid = session.current_patient.patient_id
    scenarios = list(session.selected_scenarios)
    client = PatientListClient(
        Path("app/patient_import/patientenTagesliste.json")
    )
    client.update_prepared_scenarios(pid, scenarios)
    global PATIENTS
    PATIENTS = client.load_patients()
    for p in PATIENTS:
        if p.patient_id == pid:
            session.current_patient = p
            break
    ui.notify(
        f"Szenarien für {_format_patient_name(session.current_patient)} gespeichert.",
        color="positive",
    )
    refresh_ui()


def _set_staff_scenarios(session: BrowserSession, scenario_keys) -> None:
    if not isinstance(scenario_keys, list):
        scenario_keys = []
    allowed = {scenario["key"] for scenario in SCENARIOS}
    session.selected_scenarios = sorted(
        {
            str(key).strip().upper()
            for key in scenario_keys
            if str(key).strip().upper() in allowed
        }
    )


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


def _find_loaded_patient(patient_id: str) -> PatientRecord | None:
    for patient in PATIENTS:
        if patient.patient_id == patient_id:
            return patient
    return None


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


def _split_multiline_field(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(line.strip() for line in str(value).splitlines() if line.strip())


def _form_text_value(field: object, fallback: str = "") -> str:
    value = getattr(field, "value", None)
    if value is None:
        return fallback
    return str(value)


def _open_new_patient_dialog(
    session: BrowserSession,
    refresh_ui: Callable[[], None],
    edit_patient: PatientRecord | None = None,
) -> None:
    dialog = ui.dialog()
    dialog_style = "w-[600px] max-w-full p-6"
    max_birth_date = date.today().isoformat()
    with dialog, ui.card().classes(dialog_style):
        title = "Patient bearbeiten" if edit_patient else "Neuen Patienten anlegen"
        ui.label(title).classes("text-xl font-semibold mb-4")
        ui.label(
            "Vorname, Nachname und Geburtsdatum sind Pflichtfelder."
        ).classes("text-sm text-slate-500 mb-2")

        # --- Stammdaten ---
        with ui.card().classes("surface-card w-full shadow-none q-mb-md"):
            ui.label("Stammdaten").classes("text-base font-semibold mb-2")
            vorname = ui.input("Vorname").props("outlined required").classes("w-full")
            nachname = ui.input("Nachname").props("outlined required").classes("w-full")
            geburtsdatum = ui.input("Geburtsdatum").props(
                f"outlined required type=date max={max_birth_date}"
            ).classes("w-full")
            telefon = ui.input("Telefon").props("outlined").classes("w-full")

            with ui.row().classes("w-full gap-3"):
                with ui.column().classes("grow gap-0"):
                    gender_options = ["", "männlich", "weiblich", "divers"]
                    gender_value = (
                        edit_patient.details.gender
                        if edit_patient and edit_patient.details.gender in gender_options
                        else ""
                    )
                    geschlecht = ui.select(
                        gender_options,
                        label="Geschlecht",
                        value=gender_value,
                    ).props("outlined").classes("w-full")
                with ui.column().classes("grow gap-0"):
                    groesse = ui.input(
                        "Größe (cm)",
                        value=(
                            str(edit_patient.details.groesse_cm or "")
                            if edit_patient
                            else ""
                        ),
                    ).props("outlined type=number").classes("w-full")
            sprache = ui.input(
                "Sprache",
                value=edit_patient.details.language if edit_patient else "",
            ).props("outlined").classes("w-full")
            wohnort = ui.input(
                "Wohnort",
                value=edit_patient.details.contact_city if edit_patient else "",
            ).props("outlined").classes("w-full")
            versicherung = ui.input(
                "Versicherung",
                value=edit_patient.details.insurance if edit_patient else "",
            ).props("outlined").classes("w-full")
            if edit_patient:
                vorname.value = edit_patient.first_name
                nachname.value = edit_patient.last_name
                geburtsdatum.value = edit_patient.date_of_birth
                telefon.value = edit_patient.details.phone

        # --- Kurzinfos ---
        with ui.card().classes("surface-card w-full shadow-none q-mb-md"):
            ui.label("Kurzinfos (ein Eintrag pro Zeile)").classes("text-base font-semibold mb-2")
            with ui.row().classes("w-full gap-3"):
                with ui.column().classes("grow gap-0"):
                    dauerdiagnosen = ui.textarea(
                        "Dauerdiagnosen",
                        value=(
                            "\n".join(edit_patient.details.long_term_diagnoses)
                            if edit_patient
                            else ""
                        ),
                    ).props("outlined").classes("w-full")
                with ui.column().classes("grow gap-0"):
                    medikation = ui.textarea(
                        "Medikation",
                        value="\n".join(edit_patient.medications) if edit_patient else "",
                    ).props("outlined").classes("w-full")
            with ui.row().classes("w-full gap-3"):
                with ui.column().classes("grow gap-0"):
                    risikofaktoren = ui.textarea(
                        "Risikofaktoren",
                        value=(
                            "\n".join(edit_patient.details.risk_factors)
                            if edit_patient
                            else ""
                        ),
                    ).props("outlined").classes("w-full")
                with ui.column().classes("grow gap-0"):
                    allergien = ui.textarea(
                        "Allergien",
                        value=(
                            "\n".join(edit_patient.details.allergies)
                            if edit_patient
                            else ""
                        ),
                    ).props("outlined").classes("w-full")

        # --- Nächster Termin ---
        with ui.card().classes("surface-card w-full shadow-none q-mb-md"):
            ui.label("Nächster Termin").classes("text-base font-semibold mb-2")
            termindatum = ui.input(
                "Datum/Uhrzeit",
                value=edit_patient.details.next_appointment_at if edit_patient else "",
            ).props("outlined type=datetime-local").classes("w-full")
            terminart = ui.input(
                "Art",
                value=edit_patient.details.next_appointment_type if edit_patient else "",
            ).props("outlined").classes("w-full")
            terminnotiz = ui.input(
                "Hinweis",
                value=edit_patient.details.next_appointment_note if edit_patient else "",
            ).props("outlined").classes("w-full")
        # --- Notizen ---
        notizen = ui.textarea("Notizen").props("outlined").classes("w-full")
        if edit_patient:
            notizen.value = edit_patient.details.notes

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Abbrechen", on_click=dialog.close).props("outline")

            def save() -> None:
                pid = edit_patient.patient_id if edit_patient else _generate_patient_id()

                orig_details = edit_patient.details if edit_patient else PatientDetails()
                orig_dob = edit_patient.date_of_birth if edit_patient else ""
                orig_first = edit_patient.first_name if edit_patient else ""
                orig_last = edit_patient.last_name if edit_patient else ""
                first = normalize_person_name(vorname.value or orig_first)
                last = normalize_person_name(nachname.value or orig_last)

                if not first or not last:
                    ui.notify(
                        "Vorname und Nachname sind Pflichtfelder.",
                        color="negative",
                    )
                    return

                try:
                    birth_date = _parse_required_iso_birth_date(
                        geburtsdatum.value or orig_dob
                    )
                except ValueError as exc:
                    ui.notify(str(exc), color="negative")
                    return

                duplicate = _find_duplicate_patient(
                    first,
                    last,
                    birth_date,
                    exclude_patient_id=edit_patient.patient_id if edit_patient else None,
                )
                if duplicate is not None:
                    ui.notify(
                        f"Dieser Patient existiert bereits ({duplicate.patient_id}).",
                        color="warning",
                    )
                    return

                def _lines(field) -> tuple[str, ...]:
                    return _split_multiline_field(getattr(field, "value", None))

                details = PatientDetails(
                    phone=_form_text_value(telefon, orig_details.phone),
                    notes=_form_text_value(notizen, orig_details.notes),
                    gender=_form_text_value(geschlecht, orig_details.gender),
                    language=_form_text_value(sprache, orig_details.language),
                    contact_city=_form_text_value(wohnort, orig_details.contact_city),
                    insurance=_form_text_value(versicherung, orig_details.insurance),
                    groesse_cm=int(groesse.value) if groesse is not None and groesse.value.strip() else orig_details.groesse_cm,
                    next_appointment_at=_form_text_value(termindatum, orig_details.next_appointment_at),
                    next_appointment_type=_form_text_value(terminart, orig_details.next_appointment_type),
                    next_appointment_note=_form_text_value(terminnotiz, orig_details.next_appointment_note),
                    allergies=_lines(allergien),
                    long_term_diagnoses=_lines(dauerdiagnosen),
                    acute_diagnoses=orig_details.acute_diagnoses,
                    risk_factors=_lines(risikofaktoren),
                    medication_details=orig_details.medication_details,
                    patient_notes=orig_details.patient_notes,
                    open_tasks=orig_details.open_tasks,
                    status=orig_details.status,
                )
                orig_conds = edit_patient.conditions if edit_patient else ""
                med_list = (
                    [m.strip() for m in medikation.value.split("\n") if m.strip()]
                    if medikation is not None
                    else (edit_patient.medications if edit_patient else [])
                )
                patient = PatientRecord(
                    patient_id=pid,
                    first_name=first,
                    last_name=last,
                    date_of_birth=birth_date,
                    medications=med_list,
                    conditions=orig_conds,
                    details=details,
                    prepared_scenarios=(
                        edit_patient.prepared_scenarios if edit_patient else ()
                    ),
                    prepared_scenarios_saved=(
                        edit_patient.prepared_scenarios_saved if edit_patient else False
                    ),
                )

                client = PatientListClient(
                    Path("app/patient_import/patientenTagesliste.json")
                )
                client.append_patient(patient)
                global PATIENTS
                PATIENTS = client.load_patients()

                dialog.close()
                reloaded_patient = _find_loaded_patient(pid)
                if edit_patient:
                    session.current_patient = reloaded_patient or patient
                    if getattr(session.current_patient, "prepared_scenarios_saved", False):
                        session.selected_scenarios = list(
                            getattr(session.current_patient, "prepared_scenarios", ())
                        )
                    else:
                        recommended_ui_key = _get_recommended_scenario_ui_key(
                            session.current_patient
                        )
                        session.selected_scenarios = (
                            [recommended_ui_key] if recommended_ui_key else []
                        )
                else:
                    session.current_patient = None
                    session.selected_scenarios.clear()
                    session.staff_search_query = ""
                session.stage = "staff_selection"
                session.identity_check = IdentityCheck(PATIENTS, max_attempts=MAX_ATTEMPTS)
                ui.notify(
                    f"Patientendaten für {pid} {'aktualisiert' if edit_patient else 'angelegt'}.",
                    color="positive",
                )
                refresh_ui()

            ui.button("Patientendaten speichern", on_click=save).props("unelevated").classes(
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
                    "Mehrfachauswahl ist erlaubt. Es stehen nur die aktuell umgesetzten Szenarien zur Auswahl."
                ).classes("text-sm leading-6 text-slate-600")

                scenario_options = {
                    scenario["key"]: (
                        f"Szenario {scenario['key']} - {scenario['title']}"
                        + (" (empfohlen)" if scenario["key"] == recommended_ui_key else "")
                    )
                    for scenario in SCENARIOS
                }
                selected_keys = [
                    key for key in session.selected_scenarios if key in scenario_options
                ]
                scenario_select = ui.select(
                    scenario_options,
                    label="Szenarien",
                    value=selected_keys,
                    multiple=True,
                    clearable=True,
                    on_change=lambda e: _set_staff_scenarios(session, e.value),
                ).props("outlined use-chips").classes("w-full mt-3")
                scenario_select.tooltip(
                    "Auswahl aus Husten/Infekt, Brustschmerz, Hypertonie und Typ-2-Diabetes"
                )

            with ui.row().classes("w-full justify-end gap-3"):
                ui.button(
                    "Szenarien speichern",
                    on_click=lambda: _save_staff_scenarios(session, refresh_ui),
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

    session.reload_message = ""
    _prepare_dialogue_session(session, scenario_keys)

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
                on_click=lambda: _reset_browser_session(session, refresh_ui),
            ).props("outline")
        return

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-2"):
                ui.label(ctrl.phase_label).classes("eyebrow")
                if session.anamnesis_mode is not None:
                    ui.label("Assistierte Anamnese").classes("text-2xl font-semibold")
            if session.chat_phase_done or ctrl.state != DialogueState.ANAMNESIS:
                avatar = _get_avatar_state(session)
                with ui.row().classes("avatar-panel items-center gap-3"):
                    _render_owl_avatar(avatar["tone"], "medium")
                    with ui.column().classes("gap-0"):
                        ui.label(avatar["title"]).classes("text-sm font-semibold")
                        ui.label(avatar["subtitle"]).classes("text-xs text-slate-500")

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

        elif session.summary_ready:
            _render_red_flag_indicator(session)
        else:
            _render_guided_dialogue(session, refresh_ui)

    if session.summary_ready:
        _render_summary(session, refresh_ui)
        ui.timer(
            0.1,
            lambda: ui.run_javascript("window.scrollTo(0, 0)"),
            once=True,
        )


def _render_red_flag_indicator(session: BrowserSession) -> None:
    ctrl = session.primary_controller
    if ctrl is None or ctrl.summary is None:
        return

    summary_controllers = [
        controller
        for controller in (session.controllers or [ctrl])
        if controller is not None and controller.summary is not None
    ]
    summaries = [
        controller.summary
        for controller in summary_controllers
    ]
    if not summaries:
        summaries = [ctrl.summary]

    red_flags = [rf for item in summaries for rf in item.red_flags]

    if red_flags:
        with ui.card().classes("surface-card w-full shadow-none"):
            with ui.row().classes("w-full items-center gap-3 mb-3"):
                ui.icon("warning", size="md").classes("text-red-600")
                ui.label(
                    f"{len(red_flags)} Red Flag{'s' if len(red_flags) != 1 else ''} erkannt"
                ).classes("text-lg font-semibold text-red-700")
            for rf in red_flags:
                severity_color = "text-red-700" if rf.severity == "critical" else "text-amber-600"
                severity_icon = "error" if rf.severity == "critical" else "warning"
                with ui.row().classes("w-full items-start gap-2 py-1"):
                    ui.icon(severity_icon, size="sm").classes(severity_color)
                    with ui.column().classes("gap-0"):
                        ui.label(rf.description).classes("text-sm text-slate-700")
                        ui.label(rf.rule_id).classes("text-xs text-slate-400")
    else:
        with ui.card().classes("surface-card w-full shadow-none"):
            with ui.row().classes("w-full items-center gap-3"):
                ui.icon("check_circle", size="md").classes("text-green-600")
                ui.label("Keine Red Flags erkannt").classes(
                    "text-lg font-semibold text-green-700"
                )


def _render_summary(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    ctrl = session.primary_controller
    if ctrl is None or ctrl.summary is None:
        return

    summary = ctrl.summary
    summary_controllers = [
        controller
        for controller in (session.controllers or [ctrl])
        if controller is not None and controller.summary is not None
    ]
    summaries = [
        controller.summary
        for controller in summary_controllers
    ]
    if not summaries:
        summaries = [summary]

    scenario_text = " + ".join(
        _get_scenario_title(k) for k in session.selected_scenarios
    )

    merged_vitals: dict[str, int | float] = {}
    merged_vital_sources: dict[str, str] = {}
    for item in summaries:
        merged_vitals.update(item.vitals)
        merged_vital_sources.update(item.vital_sources)

    complete_answers: dict[str, str] = {}
    for controller in summary_controllers:
        item = controller.summary
        if item is None:
            continue
        question_labels = {
            question.key: " ".join(question.text.split())
            for question, _answer in controller.get_questions_with_answers()
        }
        scenario_prefix = f"{_get_scenario_title(item.scenario)}: " if len(summaries) > 1 else ""
        for question, _answer in controller.get_questions_with_answers():
            key = question.key
            value = str(item.answers.get(key, "")).strip()
            if not value and not controller.is_question_visible(key, item.answers):
                continue
            label = f"{scenario_prefix}{question_labels.get(key, key)}"
            display_value = "keine Angabe" if not value or value.lower() == "unbekannt" else value
            if label not in complete_answers:
                complete_answers[label] = display_value
            elif complete_answers[label] != display_value:
                complete_answers[f"{label} ({item.scenario})"] = display_value

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

    with ui.card().classes("surface-card w-full shadow-none"):
        with ui.row().classes("w-full items-center gap-3"):
            ui.icon("check_circle", size="md").classes("text-green-600")
            ui.label("Die Daten wurden erfolgreich gespeichert.").classes(
                "text-lg font-semibold text-green-700"
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

            _vital_labels = {
                "systolisch": "Systolisch",
                "diastolisch": "Diastolisch",
                "puls": "Puls",
                "spo2": "SpO2",
                "gewicht": "Gewicht",
            }
            _vital_units = {
                "systolisch": "mmHg",
                "diastolisch": "mmHg",
                "puls": "bpm",
                "spo2": "%",
                "gewicht": "kg",
            }
            _render_summary_section(
                "Vitalparameter",
                {
                    **{
                        _vital_labels.get(key, key): (
                            f"{value} {_vital_units.get(key, '')} "
                            f"(Quelle: {merged_vital_sources.get(key, summary.vitals_source)})"
                        ).strip()
                        for key, value in merged_vitals.items()
                    },
                },
            )

        red_flags = [rf for item in summaries for rf in item.red_flags]
        if red_flags:
            _render_summary_section(
                "Warnhinweise / Red Flags",
                {
                    rf.rule_id: f"{rf.severity}: {rf.description}"
                    for rf in red_flags
                },
            )

        if any(item.grouped_sections for item in summaries):
            multiple_summaries = len(summaries) > 1
            for item in summaries:
                for title, fields in item.grouped_sections.items():
                    section_title = (
                        f"{_get_scenario_title(item.scenario)}: {title}"
                        if multiple_summaries
                        else title
                    )
                    _render_summary_section(section_title, fields)
        else:
            _render_summary_section("Anamnese-Antworten", complete_answers)

        open_points: list[str] = []
        for item in summaries:
            prefix = f"{_get_scenario_title(item.scenario)}: " if len(summaries) > 1 else ""
            open_points.extend(f"{prefix}{point}" for point in item.open_points)
        if open_points:
            _render_summary_section(
                "Offene Punkte",
                {f"Punkt {index + 1}": point for index, point in enumerate(open_points)},
            )

        if complete_answers:
            _render_summary_section("Vollständige Angaben", complete_answers)


def _start_editing(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.editing_answers = True
    refresh_ui()


def _set_field_source(field: object, source: str) -> None:
    setattr(field, "measurement_source", source)
    label = getattr(field, "source_label", None)
    if label is not None:
        display_source = {
            "noch nicht erfasst": "noch nicht erfasst",
            "unbekannt": "unbekannt / nicht gemessen",
            "manuell eingegeben": "manuelle Eingabe",
            "simuliert": "Simulator",
            "per Sprache erfasst": "Spracheingabe",
            "vom Gerät gemessen": "Gerät",
        }.get(source, source)
        label.set_text(f"Ausgewählt: {display_source}")


def _set_unknown_state(is_unknown: bool | None, *controls: object) -> None:
    """Keep all controls in sync with an ``unbekannt`` checkbox."""
    for control in controls:
        if is_unknown:
            control.disable()
        else:
            control.enable()


def _mark_field_recorded(field: object | None, recorded: bool) -> None:
    if field is not None and hasattr(field, "value_recorded"):
        setattr(field, "value_recorded", recorded)


def _simulate_pulse(fields: dict[str, object]) -> dict[str, int] | None:
    puls_field = fields.get("puls")
    if not isinstance(puls_field, _SliderField):
        return None
    simulated = Simulator.simuliere_puls()
    _set_field_source(puls_field, "simuliert")
    _mark_field_recorded(puls_field, True)
    puls_field.slider.enable()
    puls_field.number_input.enable()
    puls_field.unknown_checkbox.set_value(False)
    puls_field.slider.set_value(simulated)
    puls_field.number_input.set_value(simulated)
    return {"puls": simulated}


def _simulate_oximeter_in_form(
    fields: dict[str, object], controller: DialogueController
) -> dict[str, int] | None:
    spo2_field = fields.get("spo2")
    if not isinstance(spo2_field, _SliderField):
        return None
    patient = controller.get_patient()
    sim = Simulator(
        geschlecht=patient.details.gender,
        groesse_cm=patient.details.groesse_cm,
        alter=_calculate_age(patient.date_of_birth),
    )
    result = sim.pulsoximeter()
    _set_field_source(spo2_field, "simuliert")
    _mark_field_recorded(spo2_field, True)
    spo2_field.slider.enable()
    spo2_field.number_input.enable()
    spo2_field.unknown_checkbox.set_value(False)
    spo2_field.slider.set_value(result["spo2"])
    spo2_field.number_input.set_value(result["spo2"])

    puls_field = fields.get("puls")
    if isinstance(puls_field, _SliderField):
        _set_field_source(puls_field, "simuliert")
        _mark_field_recorded(puls_field, True)
        puls_field.slider.enable()
        puls_field.number_input.enable()
        puls_field.unknown_checkbox.set_value(False)
        puls_field.slider.set_value(result["puls"])
        puls_field.number_input.set_value(result["puls"])

    return result


def _simulate_blood_pressure(fields: dict[str, object]) -> dict[str, int] | None:
    bp_field = fields.get("blutdruck_systolisch")
    if not isinstance(bp_field, _BloodPressureField):
        return None
    bp = Simulator.simuliere_blutdruck()
    _set_field_source(bp_field, "simuliert")
    _mark_field_recorded(bp_field, True)
    bp_field.unknown_checkbox.set_value(False)
    bp_field.sys_slider.set_value(bp["systolisch"])
    bp_field.sys_input.set_value(bp["systolisch"])
    bp_field.dia_slider.set_value(bp["diastolisch"])
    bp_field.dia_input.set_value(bp["diastolisch"])
    bp_field.sys_slider.enable()
    bp_field.sys_input.enable()
    bp_field.dia_slider.enable()
    bp_field.dia_input.enable()
    return bp


def _simulate_weight_in_form(
    fields: dict[str, object], controller: DialogueController
) -> dict | None:
    weight_field = fields.get("gewicht")
    if weight_field is None:
        weight_field = fields.get("gewicht_aktuell")
    if not isinstance(weight_field, _SliderField):
        return None
    patient = controller.get_patient()
    sim = Simulator(
        geschlecht=patient.details.gender,
        groesse_cm=patient.details.groesse_cm,
        alter=_calculate_age(patient.date_of_birth),
    )
    result = sim.gewicht()
    simulated = result["gewicht"]
    bmi = result["bmi"]
    klasse = result["klasse"]
    _set_field_source(weight_field, "simuliert")
    _mark_field_recorded(weight_field, True)
    weight_field.slider.enable()
    weight_field.number_input.enable()
    weight_field.unknown_checkbox.set_value(False)
    weight_field.slider.set_value(simulated)
    weight_field.number_input.set_value(simulated)
    if weight_field.info_label is not None:
        weight_field.info_label.set_text(f"BMI: {bmi} ({klasse})")
    return result


def _build_question_form(
    session: BrowserSession,
    controller: DialogueController,
    questions_with_answers: list[tuple],
    refresh_ui: Callable[[], None],
    title: str,
    description: str,
    submit_label: str,
    submit_callback: Callable[[dict[str, str], dict[str, str]], None],
    cancel_callback: Callable[[], None],
    live_visibility: bool = True,
    prefilled: dict[str, str] | None = None,
    live_escalation_callback: Callable[[dict[str, str]], bool] | None = None,
    simulator_update_callback: Callable[[str, dict], None] | None = None,
    manual_vital_callback: Callable[[str, dict[str, str]], None] | None = None,
    prefilled_vital_sources: dict[str, str] | None = None,
    ai_prefilled_keys: set[str] | None = None,
) -> None:
    if controller is None:
        return

    containers: dict[str, ui.card] = {}
    fields: dict[str, object] = {}
    q_text_map: dict[str, str] = {q.key: q.text for q, _ in questions_with_answers}
    input_types: dict[str, str] = {q.key: q.input_type for q, _ in questions_with_answers}
    required_keys: set[str] = {q.key for q, _ in questions_with_answers if q.required}
    answer_by_key: dict[str, str] = {q.key: answer for q, answer in questions_with_answers}
    prefilled_vital_sources = prefilled_vital_sources or {}
    ai_prefilled_keys = ai_prefilled_keys or set()

    def _collect_values() -> dict[str, str]:
        result: dict[str, str] = {}
        for key, field in fields.items():
            if isinstance(field, _BloodPressureField):
                result["blutdruck_systolisch"] = field.sys_value
                result["blutdruck_diastolisch"] = field.dia_value
            elif isinstance(field, _DummyField):
                continue
            else:
                value = field.value
                if value is None:
                    value = ""
                result[key] = str(value).strip()
        return result

    def _collect_vital_sources() -> dict[str, str]:
        sources: dict[str, str] = {}
        source_keys = {
            "puls": "puls",
            "spo2": "spo2",
            "gewicht": "gewicht",
            "gewicht_aktuell": "gewicht",
            "korpertemperatur": "temperatur",
            "atemfrequenz": "atemfrequenz",
        }
        for answer_key, vital_key in source_keys.items():
            field = fields.get(answer_key)
            value = _collect_values().get(answer_key, "").lower()
            if field is not None and value not in ("", "unbekannt", "nicht gemessen"):
                sources[vital_key] = getattr(
                    field, "measurement_source", "manuell eingegeben"
                )

        bp_field = fields.get("blutdruck_systolisch")
        if (
            isinstance(bp_field, _BloodPressureField)
            and bp_field.value not in ("", "unbekannt", "nicht gemessen")
        ):
            source = getattr(bp_field, "measurement_source", "manuell eingegeben")
            sources["systolisch"] = source
            sources["diastolisch"] = source
        return sources

    def _run_live_escalation() -> bool:
        if live_escalation_callback is None:
            return False
        return live_escalation_callback(_collect_values())

    def _refresh_visibility() -> None:
        if not live_visibility:
            return
        for q, _ in questions_with_answers:
            if q.key in containers:
                containers[q.key].visible = controller.is_question_visible(
                    q.key, {k: (f.value if hasattr(f, 'value') else f) for k, f in fields.items()}
                )

    def _make_radio_handler(key: str):
        def _handler(e) -> None:
            _refresh_visibility()
            _run_live_escalation()
        return _handler

    def _handle_manual_vital_change(kind: str, field: object | None = None) -> None:
        if field is not None:
            _mark_field_recorded(field, True)
            _set_field_source(field, "manuell eingegeben")
        if _run_live_escalation():
            return
        if manual_vital_callback is not None:
            manual_vital_callback(kind, _collect_values())

    def _handle_unknown_vital_change(
        is_unknown: bool,
        kind: str,
        answer_key: str,
        *controls: object,
    ) -> None:
        _set_unknown_state(is_unknown, *controls)
        field = fields.get(answer_key)
        simulator_just_supplied_value = (
            not is_unknown
            and getattr(field, "measurement_source", "") == "simuliert"
        )
        if is_unknown:
            _mark_field_recorded(field, True)
            _set_field_source(field, "unbekannt")
            if _run_live_escalation():
                return
            if manual_vital_callback is not None:
                manual_vital_callback(kind, _collect_values())
            return
        if simulator_just_supplied_value:
            _mark_field_recorded(field, True)
            _refresh_visibility()
            _run_live_escalation()
            return
        _mark_field_recorded(field, False)
        _set_field_source(field, "noch nicht erfasst")
        _refresh_visibility()
        _run_live_escalation()

    def _vital_kind_for_answer(answer_key: str) -> str:
        if answer_key == "puls":
            return "pulse"
        if answer_key == "spo2":
            return "oximeter"
        return "weight"

    def _simulate_pulse_and_check() -> None:
        result = _simulate_pulse(fields)
        if result is None:
            return
        if _run_live_escalation():
            return
        if simulator_update_callback is not None:
            simulator_update_callback("pulse", result)

    def _simulate_oximeter_and_check() -> None:
        result = _simulate_oximeter_in_form(fields, controller)
        if result is None:
            return
        if _run_live_escalation():
            return
        if simulator_update_callback is not None:
            simulator_update_callback("oximeter", result)

    def _simulate_blood_pressure_and_check() -> None:
        result = _simulate_blood_pressure(fields)
        if result is None:
            return
        if _run_live_escalation():
            return
        if simulator_update_callback is not None:
            simulator_update_callback("blood_pressure", result)

    def _simulate_weight_and_check() -> None:
        result = _simulate_weight_in_form(fields, controller)
        if result is None:
            return
        if _run_live_escalation():
            return
        if simulator_update_callback is not None:
            simulator_update_callback("weight", result)

    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            ui.label(title).classes("text-2xl font-semibold")
            ui.label(description).classes("text-[1rem] leading-7 text-slate-600")

        _render_anamnesis_mode_toolbar(session, refresh_ui, _collect_values)

        for question, answer in questions_with_answers:
            key = question.key
            effective_answer = answer
            is_prefilled = False
            if prefilled and key in prefilled and prefilled[key]:
                effective_answer = prefilled[key]
                is_prefilled = True
            is_ai_prefilled = key in ai_prefilled_keys

            label = question.text
            if key in required_keys:
                label = f"{label} *"

            card_classes = "surface-card w-full shadow-none"
            if is_ai_prefilled:
                card_classes += " border-l-4 border-l-[#17603d]"

            if key == "puls_messen":
                fields[key] = _DummyField()
                continue

            if key == "gewicht_messen":
                fields[key] = _DummyField()
                continue

            if key == "blutdruck_diastolisch":
                fields[key] = _DummyField()
                continue

            if key == "blutdruck_messen":
                fields[key] = _DummyField()
                continue

            if key == "blutdruck_systolisch":
                sys_answer = str(
                    (prefilled or {}).get(
                        "blutdruck_systolisch",
                        answer_by_key.get("blutdruck_systolisch", ""),
                    )
                ).strip()
                dia_answer = str(
                    (prefilled or {}).get(
                        "blutdruck_diastolisch",
                        answer_by_key.get("blutdruck_diastolisch", ""),
                    )
                ).strip()
                explicit_unknown = (
                    sys_answer.lower() == "unbekannt"
                    or dia_answer.lower() == "unbekannt"
                )
                has_recorded_bp = bool(sys_answer and dia_answer and not explicit_unknown)
                try:
                    initial_sys = int(float(sys_answer.replace(",", ".")))
                except ValueError:
                    initial_sys = 120
                try:
                    initial_dia = int(float(dia_answer.replace(",", ".")))
                except ValueError:
                    initial_dia = 80

                with ui.card().classes(card_classes) as card:
                    containers[key] = card
                    with ui.column().classes("w-full gap-3"):
                        ui.label(
                            "Wie hoch war Ihr letzter gemessener Blutdruck?\n"
                            "Bitte tragen Sie den oberen und den unteren Wert ein."
                        ).classes(
                            "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
                        )
                        with ui.column().classes("w-full gap-1"):
                            sys_slider = ui.slider(
                                min=80, max=250, step=1, value=initial_sys
                            ).classes("w-full")
                            sys_input = ui.number(
                                "Oberer Wert", value=initial_sys, min=80, max=250, step=1
                            ).props("outlined").classes(
                                "w-full sm:max-w-[220px]"
                            )
                            sys_slider.on(
                                "update:model-value",
                                lambda e: sys_input.set_value(int(float(e.args))),
                            )
                            sys_input.on(
                                "update:model-value",
                                lambda e: sys_slider.set_value(int(float(e.args)))
                                if e.args not in (None, "") else None,
                            )
                        with ui.column().classes("w-full gap-1"):
                            dia_slider = ui.slider(
                                min=40, max=150, step=1, value=initial_dia
                            ).classes("w-full")
                            dia_input = ui.number(
                                "Unterer Wert", value=initial_dia, min=40, max=150, step=1
                            ).props("outlined").classes(
                                "w-full sm:max-w-[220px]"
                            )
                            dia_slider.on(
                                "update:model-value",
                                lambda e: dia_input.set_value(int(float(e.args))),
                            )
                            dia_input.on(
                                "update:model-value",
                                lambda e: dia_slider.set_value(int(float(e.args)))
                                if e.args not in (None, "") else None,
                            )
                        unknown_checkbox = ui.checkbox(
                            "unbekannt", value=explicit_unknown
                        )
                        _set_unknown_state(
                            explicit_unknown, sys_slider, sys_input, dia_slider, dia_input
                        )
                        unknown_checkbox.on_value_change(
                            lambda e: _handle_unknown_vital_change(
                                bool(e.value),
                                "blood_pressure",
                                key,
                                sys_slider,
                                sys_input,
                                dia_slider,
                                dia_input,
                            )
                        )
                fields[key] = _BloodPressureField(
                    sys_slider,
                    sys_input,
                    dia_slider,
                    dia_input,
                    unknown_checkbox,
                    has_recorded_bp or explicit_unknown,
                )
                source_label = ui.label(
                    "Ausgewählt: manuelle Eingabe"
                ).classes("text-sm font-medium text-[#0f766e]")
                fields[key].source_label = source_label
                fields[key].measurement_source = (
                    "unbekannt"
                    if explicit_unknown
                    else prefilled_vital_sources.get(
                        "systolisch",
                        "manuell eingegeben" if has_recorded_bp else "noch nicht erfasst",
                    )
                )
                _set_field_source(fields[key], fields[key].measurement_source)
                sys_slider.on(
                    "change",
                    lambda _, field=fields[key]: _handle_manual_vital_change(
                        "blood_pressure", field
                    ),
                )
                dia_slider.on(
                    "change",
                    lambda _, field=fields[key]: _handle_manual_vital_change(
                        "blood_pressure", field
                    ),
                )
                sys_input.on(
                    "blur",
                    lambda _, field=fields[key]: _handle_manual_vital_change(
                        "blood_pressure", field
                    ),
                )
                dia_input.on(
                    "blur",
                    lambda _, field=fields[key]: _handle_manual_vital_change(
                        "blood_pressure", field
                    ),
                )
                ui.button(
                    "Blutdruck-Simulator verwenden",
                    on_click=_simulate_blood_pressure_and_check,
                ).props("outline").classes("w-fit text-[#0f766e]")
                continue

            with ui.card().classes(card_classes) as card:
                containers[key] = card
                ui.label(label).classes(
                    "whitespace-pre-wrap text-[0.97rem] leading-7 text-slate-600"
                )
                if is_ai_prefilled:
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
                        answer_text = str(effective_answer).strip()
                        explicit_unknown = answer_text.lower() == "unbekannt"

                        try:
                            init_val = float(answer_text.replace(",", "."))
                            has_recorded_value = True
                        except (ValueError, AttributeError):
                            init_val = min_val
                            has_recorded_value = False

                        init_val = max(min_val, min(max_val, init_val))
                        vital_slider_keys = {"puls", "spo2", "gewicht", "gewicht_aktuell"}

                        with ui.column().classes("w-full gap-1"):
                            slider = ui.slider(
                                min=min_val, max=max_val, step=step, value=init_val
                            ).classes("w-full")
                            number_input = ui.number(
                                "Messwert",
                                value=init_val if step < 1 else int(init_val),
                                min=min_val,
                                max=max_val,
                                step=step,
                            ).props("outlined").classes(
                                "w-full sm:max-w-[220px]"
                            )
                            slider.on(
                                "update:model-value",
                                lambda e, inp=number_input: inp.set_value(
                                    float(e.args)
                                ),
                            )
                            number_input.on(
                                "update:model-value",
                                lambda e, s=slider: s.set_value(float(e.args))
                                if e.args not in (None, "") else None,
                            )

                            unknown_checkbox = ui.checkbox(
                                "unbekannt", value=explicit_unknown
                            )
                            _set_unknown_state(explicit_unknown, slider, number_input)
                            unknown_checkbox.on_value_change(
                                lambda e, s=slider, inp=number_input, answer_key=key: (
                                    _handle_unknown_vital_change(
                                        bool(e.value),
                                        _vital_kind_for_answer(answer_key),
                                        answer_key,
                                        s,
                                        inp,
                                    )
                                    if answer_key in ("puls", "spo2", "gewicht", "gewicht_aktuell")
                                    else (
                                        _set_unknown_state(e.value, s, inp),
                                        _refresh_visibility(),
                                        _run_live_escalation(),
                                    )
                                )
                            )

                        fields[key] = _SliderField(
                            slider,
                            unknown_checkbox,
                            number_input,
                            min_val,
                            max_val,
                            step,
                            value_recorded=has_recorded_value or explicit_unknown,
                        )
                        slider.on(
                            "change",
                            lambda _, field=fields[key]: _mark_field_recorded(
                                field, True
                            ),
                        )
                        number_input.on(
                            "blur",
                            lambda _, field=fields[key]: _mark_field_recorded(
                                field, True
                            ),
                        )
                        if key in ("gewicht", "gewicht_aktuell"):
                            fields[key].info_label = ui.label("").classes(
                                "text-sm font-medium text-slate-600"
                            )
                        if key in ("puls", "spo2", "gewicht", "gewicht_aktuell"):
                            source_label = ui.label(
                                "Ausgewählt: manuelle Eingabe"
                            ).classes("text-sm font-medium text-[#0f766e]")
                            fields[key].source_label = source_label
                            vital_source_key = (
                                "gewicht" if key in ("gewicht", "gewicht_aktuell") else key
                            )
                            fields[key].measurement_source = (
                                "unbekannt"
                                if explicit_unknown
                                else prefilled_vital_sources.get(
                                    vital_source_key,
                                    "manuell eingegeben"
                                    if has_recorded_value
                                    else "noch nicht erfasst",
                                )
                            )
                            _set_field_source(fields[key], fields[key].measurement_source)
                            slider.on(
                                "change",
                                lambda _, field=fields[key], answer_key=key:
                                    _handle_manual_vital_change(
                                        _vital_kind_for_answer(answer_key),
                                        field,
                                    ),
                            )
                            number_input.on(
                                "blur",
                                lambda _, field=fields[key], answer_key=key:
                                    _handle_manual_vital_change(
                                        _vital_kind_for_answer(answer_key),
                                        field,
                                    ),
                            )
                            if key == "puls":
                                ui.button(
                                    "Puls-Simulator verwenden",
                                    on_click=_simulate_pulse_and_check,
                                ).props("outline").classes("w-fit text-[#0f766e]")
                            elif key == "spo2":
                                ui.button(
                                    "Pulsoximeter-Simulator verwenden",
                                    on_click=_simulate_oximeter_and_check,
                                ).props("outline").classes("w-fit text-[#0f766e]")
                            else:
                                ui.button(
                                    "Gewichts-Simulator verwenden",
                                    on_click=_simulate_weight_and_check,
                                ).props("outline").classes("w-fit text-[#0f766e]")
                    else:
                        inp = ui.input(
                            value=effective_answer,
                            placeholder="Zahl eingeben oder 'unbekannt'",
                        ).classes("w-full").props("outlined")
                        inp.on("blur", lambda _: _run_live_escalation())
                        fields[key] = inp
                else:
                    ta = ui.textarea(
                        value=effective_answer,
                        placeholder="Ihre Antwort",
                    ).classes("w-full").props("outlined")
                    ta.on("blur", lambda _: _run_live_escalation())
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
            errors: list[str] = []

            collected = _collect_values()
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

        def _missing_vital_labels(collected: dict[str, str]) -> tuple[str, ...]:
            labels_by_key = {
                "blutdruck_systolisch": "Blutdruck",
                "puls": "Puls",
                "spo2": "Sauerstoffsaettigung",
                "gewicht": "Gewicht",
                "gewicht_aktuell": "Gewicht",
            }
            missing: list[str] = []
            seen: set[str] = set()
            for answer_key, label_text in labels_by_key.items():
                if answer_key not in fields:
                    continue
                container = containers.get(answer_key)
                if container is not None and not container.visible:
                    continue
                if label_text in seen:
                    continue
                value = str(collected.get(answer_key, "")).strip().lower()
                if value in ("", "unbekannt", "nicht gemessen"):
                    seen.add(label_text)
                    missing.append(label_text)
            return tuple(missing)

        confirmed_missing_vitals: tuple[str, ...] | None = None
        missing_vital_confirmation_open = False

        def _finalize_submit(collected: dict[str, str]) -> None:
            if _run_live_escalation():
                return
            submit_callback(collected, _collect_vital_sources())

        def _open_missing_vitals_confirmation(
            missing_labels: tuple[str, ...],
            collected: dict[str, str],
        ) -> None:
            nonlocal confirmed_missing_vitals, missing_vital_confirmation_open
            if missing_vital_confirmation_open:
                return

            missing_vital_confirmation_open = True
            dialog = ui.dialog().props("persistent")
            with dialog, ui.card().classes("w-[560px] max-w-full p-6"):
                ui.label("Vitalwerte fehlen").classes(
                    "text-xl font-semibold text-[#b55a07]"
                )
                ui.label(
                    "Folgende wichtige Werte wurden nicht erfasst oder als unbekannt markiert. "
                    "Bitte pruefen Sie, ob das so bleiben soll."
                ).classes("text-[0.97rem] leading-7 text-slate-600")
                for label_text in missing_labels:
                    ui.label(f"- {label_text}").classes(
                        "text-sm leading-6 text-slate-700"
                    )

                def _confirm_missing_vitals() -> None:
                    nonlocal confirmed_missing_vitals, missing_vital_confirmation_open
                    confirmed_missing_vitals = missing_labels
                    missing_vital_confirmation_open = False
                    dialog.close()
                    _finalize_submit(collected)

                def _correct_missing_vitals() -> None:
                    nonlocal missing_vital_confirmation_open
                    missing_vital_confirmation_open = False
                    dialog.close()

                with ui.row().classes("w-full justify-end gap-3 mt-4"):
                    ui.button("Werte ergaenzen", on_click=_correct_missing_vitals).props(
                        "outline"
                    )
                    ui.button(
                        "Trotzdem fortfahren",
                        on_click=_confirm_missing_vitals,
                    ).props("unelevated").classes("bg-[#b55a07] text-white")

            dialog.open()

        def _on_submit() -> None:
            nonlocal confirmed_missing_vitals
            session.critical_confirmation_open = False
            errors = _collect_and_validate()
            if errors:
                confirmed_missing_vitals = None
                ui.notify(
                    "Bitte korrigieren Sie folgende Fehler:\n" + "\n".join(errors),
                    color="negative",
                    multi_line=True,
                )
                return
            collected = _collect_values()
            missing_vitals = _missing_vital_labels(collected)
            if missing_vitals and confirmed_missing_vitals != missing_vitals:
                _open_missing_vitals_confirmation(missing_vitals, collected)
                return
            _finalize_submit(collected)

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
    _dismiss_critical_warning()
    session.controller = None
    session.controllers.clear()
    session.selected_scenarios.clear()
    session.messages.clear()
    session.pending_input = None
    session.anamnesis_mode = None
    session.chat_phase_done = False
    session.critical_confirmation_open = False
    session.guided_started = False
    session.prefilled_answers.clear()
    session.draft_answers.clear()
    session.guided_answer_message_keys.clear()
    session.guided_answer_message_values.clear()
    session.guided_answer_message_indices.clear()
    session.ai_prefilled_keys.clear()
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
                    on_click=lambda: _switch_anamnesis_mode(
                        session,
                        "guided",
                        refresh_ui,
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
                    on_click=lambda: _switch_anamnesis_mode(
                        session,
                        "form",
                        refresh_ui,
                    ),
                ).props("outline").classes(
                    "mt-4 w-full border-[var(--app-accent)] text-[var(--app-accent)]"
                )


def _render_anamnesis_mode_toolbar(
    session: BrowserSession,
    refresh_ui: Callable[[], None],
    collect_answers: Callable[[], dict[str, str]] | None = None,
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
                on_click=lambda: _switch_anamnesis_mode(
                    session,
                    "guided",
                    refresh_ui,
                    collect_answers() if collect_answers is not None else None,
                ),
            ).props("unelevated").classes("bg-[#0f766e] text-white")
            ui.button(
                "Formular verwenden",
                on_click=lambda: _switch_anamnesis_mode(
                    session,
                    "form",
                    refresh_ui,
                    collect_answers() if collect_answers is not None else None,
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

        async def _on_submit_chat() -> None:
            text = (symptom_input.value or "").strip()
            session.chat_input_text = text

            if not text:
                ui.notify(
                    "Bitte beschreiben Sie Ihre Beschwerden oder klicken Sie auf 'Ueberspringen'.",
                    color="warning",
                )
                return

            questions = [q for q, _ in ctrl.get_questions_with_answers()]

            # Lade-Dialog mit Spinner anzeigen, solange die KI auswertet.
            # Der eigentliche (blockierende) Aufruf laeuft in einem Thread,
            # damit die Oberflaeche nicht einfriert und der Hinweis sichtbar ist.
            with ui.dialog() as loading_dialog, ui.card().classes(
                "items-center gap-4 p-6"
            ):
                loading_dialog.props("persistent")
                ui.spinner(size="lg", color="#0f766e")
                ui.label("Die KI wertet Ihre Angaben aus …").classes(
                    "text-base font-medium"
                )
                ui.label(
                    "Bitte einen Moment Geduld, der Fragebogen wird vorbereitet."
                ).classes("text-sm text-slate-500")
            loading_dialog.open()

            try:
                prefilled = await run.io_bound(extract_answers, text, questions)
            finally:
                loading_dialog.close()

            controllers = session.controllers or ([ctrl] if ctrl is not None else [])
            if _apply_symptom_chat_prefill(
                session,
                prefilled,
                controllers,
                refresh_ui,
            ):
                return

            if prefilled:
                ui.notify(
                    f"KI hat {len(prefilled)} Frage(n) vorausgefüllt.",
                    color="positive",
                    position="top",
                )
            else:
                ui.notify(
                    "Die KI konnte keine Angaben übernehmen. "
                    "Bitte füllen Sie den Fragebogen manuell aus.",
                    color="warning",
                    position="top",
                    multi_line=True,
                )
            refresh_ui()

        def _on_skip() -> None:
            session.prefilled_answers = {}
            session.draft_answers.clear()
            session.guided_answer_message_keys.clear()
            session.guided_answer_message_values.clear()
            session.guided_answer_message_indices.clear()
            session.ai_prefilled_keys.clear()
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


def _apply_symptom_chat_prefill(
    session: BrowserSession,
    prefilled: dict[str, str],
    controllers: list[DialogueController],
    refresh_ui: Callable[[], None],
) -> bool:
    """Speichert KI-/Spracheingaben und prueft sofort auf kritische Red Flags."""
    session.prefilled_answers = dict(prefilled)
    session.ai_prefilled_keys = set(prefilled)
    session.chat_phase_done = True
    _remember_draft_answers(session, prefilled)

    if not prefilled:
        return False

    return _check_live_form_escalation(
        session,
        controllers,
        prefilled,
        refresh_ui,
        refresh_on_correct=True,
    )


def _answer_keys_from_red_flags(
    red_flags: list[object],
    answers: dict[str, str],
) -> set[str]:
    trigger_text = " ".join(
        str(getattr(flag, "triggered_by", "")) for flag in red_flags
    ).lower()
    aliases_by_key = {
        "blutdruck_systolisch": ("systolisch",),
        "blutdruck_diastolisch": ("diastolisch",),
        "korpertemperatur": ("temperatur", "koerpertemperatur", "körpertemperatur"),
    }

    keys: set[str] = set()
    for key in answers:
        aliases = (key, *aliases_by_key.get(key, ()))
        if any(alias.lower() in trigger_text for alias in aliases):
            keys.add(key)

    if "blutdruck_systolisch" in keys or "blutdruck_diastolisch" in keys:
        keys.update(
            key
            for key in ("blutdruck_systolisch", "blutdruck_diastolisch")
            if key in answers
        )

    return keys


def _clear_prefilled_red_flag_values_for_correction(
    session: BrowserSession,
    answers: dict[str, str],
    red_flags: list[object],
) -> set[str]:
    keys = _answer_keys_from_red_flags(red_flags, answers)
    if not keys and len(answers) == 1:
        keys = set(answers)

    for key in keys:
        session.prefilled_answers.pop(key, None)
        session.ai_prefilled_keys.discard(key)

    return keys


def _check_live_form_escalation(
    session: BrowserSession,
    controllers: list[DialogueController],
    answers: dict[str, str],
    refresh_ui: Callable[[], None],
    vitals: dict[str, int | float] | None = None,
    refresh_on_correct: bool = False,
) -> bool:
    """Fordert vor einer Eskalation die Bestätigung der kritischen Angabe an."""
    if session.critical_confirmation_open:
        return True

    for ctrl in controllers:
        flags = ctrl.preview_partial_red_flags(answers, vitals)
        critical_flags = [flag for flag in flags if flag.severity == "critical"]
        if not critical_flags:
            continue

        session.critical_confirmation_open = True
        dialog = ui.dialog().props("persistent")
        with dialog, ui.card().classes("w-[560px] max-w-full p-6"):
            with ui.row().classes("w-full items-center gap-4"):
                _render_owl_avatar("alert", "medium")
                with ui.column().classes("gap-1"):
                    ui.label("Kritische Angabe bestätigen").classes(
                        "text-xl font-semibold text-[#9f1d20]"
                    )
                    ui.label("Warnhinweis erkannt").classes(
                        "text-sm font-medium text-[#9f1d20]"
                    )
            ui.label(
                "Mindestens eine Ihrer Angaben liegt in einem kritischen Bereich. "
                "Bitte prüfen Sie den eingegebenen Messwert. Erst nach Ihrer "
                "Bestätigung wird die Anamnese abgeschlossen und das Praxisteam informiert."
            ).classes("text-[0.97rem] leading-7 text-slate-600")
            for flag in critical_flags:
                ui.label(f"• {flag.description}").classes(
                    "text-sm leading-6 text-slate-700"
                )

            def _confirm_escalation() -> None:
                session.critical_confirmation_open = False
                dialog.close()
                if not ctrl.check_partial_answers_for_escalation(answers, vitals):
                    return
                session.pending_input = None
                if session.controllers and ctrl in session.controllers:
                    session.controllers.remove(ctrl)
                    session.controllers.insert(0, ctrl)
                session.prefilled_answers.update(answers)
                ui.notify(
                    "Kritisches Warnzeichen bestätigt. Bitte sofort das Praxisteam informieren.",
                    color="negative",
                    close_button="Schließen",
                    classes="critical-red-flag-notification",
                    multi_line=True,
                    timeout=0,
                )
                refresh_ui()

            def _correct_value() -> None:
                session.critical_confirmation_open = False
                dialog.close()
                if refresh_on_correct:
                    _clear_prefilled_red_flag_values_for_correction(
                        session,
                        answers,
                        critical_flags,
                    )
                    refresh_ui()

            with ui.row().classes("w-full justify-end gap-3 mt-4"):
                ui.button("Wert korrigieren", on_click=_correct_value).props("outline")
                ui.button(
                    "Kritischen Wert bestätigen", on_click=_confirm_escalation
                ).props("unelevated").classes("bg-[#9f1d20] text-white")

        dialog.open()
        return True
    return False


def _dismiss_critical_warning() -> None:
    """Close persistent red-flag notifications from a previous patient."""
    ui.run_javascript(
        "document.querySelectorAll('.critical-red-flag-notification "
        ".q-notification__actions button').forEach(button => button.click());"
    )


def _begin_guided_questions(session: BrowserSession) -> None:
    """Startet den geführten Dialog nach dem KI-Vorab-Chat.

    Übernimmt die KI-Vorschläge in die Controller und überspringt die dadurch
    bereits beantworteten Fragen. Wird genau einmal pro Anamnese ausgelöst.
    """
    if session.guided_started:
        return
    session.guided_started = True

    controllers = session.controllers or (
        [session.primary_controller] if session.primary_controller else []
    )
    answers = _merged_anamnesis_answers(session, controllers)
    _append_guided_answer_history(session, controllers, answers)
    for ctrl in controllers:
        if ctrl is not None and ctrl.state == DialogueState.ANAMNESIS:
            ctrl.begin_anamnesis(answers)


def _device_prefilled_answers(session: BrowserSession) -> dict[str, str]:
    prefilled: dict[str, str] = {}
    if session.simulated_bp:
        prefilled["blutdruck_systolisch"] = str(session.simulated_bp["systolisch"])
        prefilled["blutdruck_diastolisch"] = str(session.simulated_bp["diastolisch"])
    if session.simulated_weight:
        weight = session.simulated_weight.get("gewicht")
        if weight is not None:
            prefilled["gewicht"] = str(weight)
            prefilled["gewicht_aktuell"] = str(weight)
    if session.simulated_oximeter:
        spo2 = session.simulated_oximeter.get("spo2")
        if spo2 is not None:
            prefilled["spo2"] = str(spo2)
        pulse = session.simulated_oximeter.get("puls")
        if pulse is not None:
            prefilled["puls"] = str(pulse)
    return prefilled


def _merged_prefilled_answers(session: BrowserSession) -> dict[str, str]:
    merged = dict(session.prefilled_answers)
    merged.update(_device_prefilled_answers(session))
    return merged


def _device_prefilled_sources(session: BrowserSession) -> dict[str, str]:
    sources: dict[str, str] = {}
    if session.simulated_bp:
        sources["systolisch"] = "simuliert"
        sources["diastolisch"] = "simuliert"
    if session.simulated_weight:
        sources["gewicht"] = "simuliert"
    if session.simulated_oximeter:
        if session.simulated_oximeter.get("spo2") is not None:
            sources["spo2"] = "simuliert"
        if session.simulated_oximeter.get("puls") is not None:
            sources["puls"] = "simuliert"
    return sources


def _update_simulator_state_from_form(
    session: BrowserSession,
    kind: str,
    values: dict,
) -> None:
    controllers = session.controllers or ([session.controller] if session.controller else [])
    if kind == "blood_pressure":
        session.simulated_bp = values
        vital_values = {
            "systolisch": values["systolisch"],
            "diastolisch": values["diastolisch"],
        }
    elif kind == "weight":
        session.simulated_weight = values
        vital_values = {"gewicht": values["gewicht"]}
    elif kind == "pulse":
        session.simulated_oximeter = {"puls": values["puls"]}
        vital_values = {"puls": values["puls"]}
    elif kind == "oximeter":
        session.simulated_oximeter = values
        vital_values = {"spo2": values["spo2"]}
        if values.get("puls") is not None:
            vital_values["puls"] = values["puls"]
    else:
        return

    for controller in controllers:
        if controller is not None:
            controller.record_vitals(vital_values, "simuliert")


def _number_from_answer(value: str | None) -> float | None:
    if value is None:
        return None
    value = str(value).strip().replace(",", ".")
    if not value or value.lower() in ("unbekannt", "nicht gemessen"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _clear_simulator_state_for_manual_input(
    session: BrowserSession,
    kind: str,
    answers: dict[str, str],
) -> None:
    controllers = session.controllers or ([session.controller] if session.controller else [])

    if kind == "blood_pressure":
        session.simulated_bp = None
        for answer_key in ("blutdruck_systolisch", "blutdruck_diastolisch"):
            if answer_key in answers:
                session.prefilled_answers[answer_key] = answers[answer_key]
        systolic = _number_from_answer(answers.get("blutdruck_systolisch"))
        diastolic = _number_from_answer(answers.get("blutdruck_diastolisch"))
        if systolic is None or diastolic is None:
            for controller in controllers:
                if controller is not None:
                    controller.clear_vitals(("systolisch", "diastolisch"))
            return
        for controller in controllers:
            if controller is not None:
                controller.record_vitals(
                    {"systolisch": systolic, "diastolisch": diastolic},
                    "manuell eingegeben",
                )
        return

    if kind == "weight":
        session.simulated_weight = None
        for answer_key in ("gewicht", "gewicht_aktuell"):
            if answer_key in answers:
                session.prefilled_answers[answer_key] = answers[answer_key]
        weight = _number_from_answer(
            answers.get("gewicht_aktuell") or answers.get("gewicht")
        )
        if weight is None:
            for controller in controllers:
                if controller is not None:
                    controller.clear_vitals(("gewicht",))
            return
        for controller in controllers:
            if controller is not None:
                controller.record_vitals({"gewicht": weight}, "manuell eingegeben")
        return

    if kind == "pulse":
        session.simulated_oximeter = None
        if "puls" in answers:
            session.prefilled_answers["puls"] = answers["puls"]
        pulse = _number_from_answer(answers.get("puls"))
        if pulse is None:
            for controller in controllers:
                if controller is not None:
                    controller.clear_vitals(("puls",))
            return
        for controller in controllers:
            if controller is not None:
                controller.record_vitals({"puls": pulse}, "manuell eingegeben")
        return

    if kind == "oximeter":
        session.simulated_oximeter = None
        if "spo2" in answers:
            session.prefilled_answers["spo2"] = answers["spo2"]
        spo2 = _number_from_answer(answers.get("spo2"))
        if spo2 is None:
            for controller in controllers:
                if controller is not None:
                    controller.clear_vitals(("spo2",))
            return
        for controller in controllers:
            if controller is not None:
                controller.record_vitals({"spo2": spo2}, "manuell eingegeben")


def _render_mass_anamnesis_single(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    ctrl = session.primary_controller
    if ctrl is None:
        return

    if session.anamnesis_mode is None:
        _render_anamnesis_mode_choice(session, refresh_ui)
        return

    # Der KI-Vorab-Chat läuft jetzt vor BEIDEN Modi (geführt und Formular).
    if not session.chat_phase_done:
        _render_symptom_chat(session, refresh_ui)
        return

    if session.anamnesis_mode == "guided":
        _begin_guided_questions(session)
        _render_anamnesis_mode_toolbar(session, refresh_ui)
        _render_guided_dialogue(session, refresh_ui)
        return

    questions_with_answers = ctrl.get_questions_with_answers()

    def _on_submit(answers: dict[str, str], vital_sources: dict[str, str]) -> None:
        try:
            _remember_draft_answers(session, answers)
            ctrl.submit_mass_anamnesis(answers, vital_sources)
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    def _on_cancel() -> None:
        session.show_cancel_dialog = True
        refresh_ui()

    _build_question_form(
        session=session,
        controller=ctrl,
        questions_with_answers=questions_with_answers,
        refresh_ui=refresh_ui,
        title="Anamnese",
        description=(
            "Alle Fragen auf einen Blick. Pflichtfelder sind mit * markiert. "
            "Einige Fragen werden dynamisch ein- oder ausgeblendet."
        ),
        submit_label="Absenden",
        submit_callback=_on_submit,
        cancel_callback=_on_cancel,
        live_visibility=True,
        prefilled=_merged_anamnesis_answers(session, [ctrl]),
        live_escalation_callback=lambda answers: _check_live_form_escalation(
            session, [ctrl], answers, refresh_ui
        ),
        simulator_update_callback=lambda kind, values: (
            _update_simulator_state_from_form(session, kind, values),
            refresh_ui(),
        ),
        manual_vital_callback=lambda kind, answers: (
            _clear_simulator_state_for_manual_input(session, kind, answers),
            refresh_ui(),
        ),
        prefilled_vital_sources=_device_prefilled_sources(session),
        ai_prefilled_keys=session.ai_prefilled_keys,
    )


def _render_mass_anamnesis_multi(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    controllers = session.controllers
    if not controllers:
        return

    if session.anamnesis_mode is None:
        _render_anamnesis_mode_choice(session, refresh_ui)
        return

    # Der KI-Vorab-Chat läuft jetzt vor BEIDEN Modi (geführt und Formular).
    if not session.chat_phase_done:
        _render_symptom_chat(session, refresh_ui)
        return

    if session.anamnesis_mode == "guided":
        _begin_guided_questions(session)
        _render_anamnesis_mode_toolbar(session, refresh_ui)
        _render_guided_dialogue(session, refresh_ui)
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

    required_keys_all: set[str] = set()
    q_text_map: dict[str, str] = {}
    input_types: dict[str, str] = {}
    for ctrl, q, answer in merged:
        required_keys_all.add(q.key) if q.required else None
        q_text_map[q.key] = q.text
        input_types[q.key] = q.input_type

    def _on_submit(answers: dict[str, str], vital_sources: dict[str, str]) -> None:
        try:
            _remember_draft_answers(session, answers)
            for ctrl in controllers:
                ctrl.submit_mass_anamnesis(answers, vital_sources)
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    def _on_cancel() -> None:
        session.show_cancel_dialog = True
        refresh_ui()

    scenario_text = " + ".join(
        _get_scenario_title(k) for k in session.selected_scenarios
    )

    _build_question_form(
        session=session,
        controller=controllers[0],
        questions_with_answers=questions_with_answers,
        refresh_ui=refresh_ui,
        title=f"Anamnese — {scenario_text}",
        description=(
            f"Alle Fragen aus den ausgewählten Szenarien auf einen Blick. "
            f"Pflichtfelder sind mit * markiert. "
            f"Einige Fragen werden dynamisch ein- oder ausgeblendet."
        ),
        submit_label="Absenden",
        submit_callback=_on_submit,
        cancel_callback=_on_cancel,
        live_visibility=True,
        prefilled=_merged_anamnesis_answers(session, controllers),
        live_escalation_callback=lambda answers: _check_live_form_escalation(
            session, controllers, answers, refresh_ui
        ),
        simulator_update_callback=lambda kind, values: (
            _update_simulator_state_from_form(session, kind, values),
            refresh_ui(),
        ),
        manual_vital_callback=lambda kind, answers: (
            _clear_simulator_state_for_manual_input(session, kind, answers),
            refresh_ui(),
        ),
        prefilled_vital_sources=_device_prefilled_sources(session),
        ai_prefilled_keys=session.ai_prefilled_keys,
    )


def _render_answer_editor(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    ctrl = session.primary_controller
    if ctrl is None:
        return

    questions_with_answers = ctrl.get_questions_with_answers()

    def _on_submit(answers: dict[str, str], vital_sources: dict[str, str]) -> None:
        try:
            _remember_draft_answers(session, answers)
            for c in session.controllers:
                c.update_answers_and_regenerate(answers, vital_sources)
            session.editing_answers = False
            refresh_ui()
        except ValueError as exc:
            ui.notify(str(exc), color="negative")

    _build_question_form(
        session=session,
        controller=ctrl,
        questions_with_answers=questions_with_answers,
        refresh_ui=refresh_ui,
        title="Antworten bearbeiten",
        description=(
            "Alle Fragen auf einen Blick. Aenderungen werden nach dem Speichern "
            "in die Zusammenfassung übernommen."
        ),
        submit_label="Speichern",
        submit_callback=_on_submit,
        cancel_callback=lambda: _cancel_editing(session, refresh_ui),
        live_visibility=True,
        prefilled=_device_prefilled_answers(session),
        live_escalation_callback=lambda answers: _check_live_form_escalation(
            session,
            session.controllers or ([ctrl] if ctrl else []),
            answers,
            refresh_ui,
        ),
        simulator_update_callback=lambda kind, values: (
            _update_simulator_state_from_form(session, kind, values),
            refresh_ui(),
        ),
        manual_vital_callback=lambda kind, answers: (
            _clear_simulator_state_for_manual_input(session, kind, answers),
            refresh_ui(),
        ),
        prefilled_vital_sources=_device_prefilled_sources(session),
        ai_prefilled_keys=session.ai_prefilled_keys,
    )


def _cancel_editing(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    session.editing_answers = False
    refresh_ui()


def _collect_questions_and_answers(
    session: BrowserSession,
) -> tuple[list, dict[str, str]]:
    """Sammelt Fragen und aktuelle Antworten über alle aktiven Controller."""
    controllers = session.controllers or (
        [session.controller] if session.controller else []
    )
    questions: list = []
    # Basis: KI-Vorausfüllungen und Gerätewerte (im Formular noch nicht
    # zwingend im Controller gespeichert), darüber die bestätigten Antworten.
    answers: dict[str, str] = {
        k: str(v).strip()
        for k, v in _merged_prefilled_answers(session).items()
        if str(v).strip()
    }
    seen_keys: set[str] = set()
    for controller in controllers:
        if controller is None:
            continue
        for question, answer in controller.get_questions_with_answers():
            if question.key not in seen_keys:
                questions.append(question)
                seen_keys.add(question.key)
            value = str(answer).strip()
            if value:
                answers[question.key] = value
    return questions, answers


def _render_assistant_chat(
    session: BrowserSession, refresh_ui: Callable[[], None]
) -> None:
    with ui.card().classes("surface-card surface-card--strong w-full shadow-none"):
        with ui.row().classes("avatar-panel w-full items-center gap-4"):
            _render_owl_avatar("listening", "large")
            with ui.column().classes("gap-1"):
                ui.label("Fragen zum Fragebogen?").classes(
                    "text-lg font-semibold"
                )
                ui.label("Ich helfe Ihnen beim Ausfüllen.").classes(
                    "text-sm text-slate-500"
                )

        with ui.scroll_area().classes(
            "chat-shell w-full rounded-2xl bg-white/45 p-3 mt-3"
        ):
            with ui.column().classes("w-full gap-3"):
                if not session.assistant_messages:
                    with ui.element("div").classes("chat-bubble chat-bubble--system"):
                        ui.label("Assistenzsystem").classes(
                            "text-[0.74rem] font-bold uppercase tracking-[0.16em] opacity-75"
                        )
                        ui.label(
                            "Sie haben eine Frage zu einer der Fragebogen-Fragen "
                            "oder einem Begriff? Schreiben Sie mir einfach – ich "
                            "erkläre es Ihnen gern."
                        ).classes("whitespace-pre-wrap text-[0.97rem] leading-7")
                else:
                    for entry in session.assistant_messages:
                        _render_message(entry)

        ui.textarea(placeholder="Ihre Frage …").props(
            "outlined rows=2 autogrow"
        ).classes("w-full mt-3").bind_value(session, "assistant_input_text")

        async def _on_send() -> None:
            text = (session.assistant_input_text or "").strip()
            if not text:
                ui.notify("Bitte geben Sie zuerst eine Frage ein.", color="warning")
                return

            session.assistant_messages.append(
                ChatEntry(role="user", text=text, tone="user")
            )
            session.assistant_input_text = ""

            questions, answers = _collect_questions_and_answers(session)
            history = [
                (entry.role, entry.text)
                for entry in session.assistant_messages[:-1]
            ]

            with ui.dialog() as loading_dialog, ui.card().classes(
                "items-center gap-4 p-6"
            ):
                loading_dialog.props("persistent")
                ui.spinner(size="lg", color="#0f766e")
                ui.label("Einen Moment, ich überlege …").classes(
                    "text-base font-medium"
                )
            loading_dialog.open()

            try:
                reply = await run.io_bound(
                    answer_question, text, questions, answers, history
                )
            finally:
                loading_dialog.close()

            offline = reply == OFFLINE_REPLY
            session.assistant_messages.append(
                ChatEntry(
                    role="system",
                    text=reply,
                    tone="warning" if offline else "system",
                )
            )
            if offline:
                ui.notify(
                    "Der KI-Assistent ist zurzeit nicht erreichbar. "
                    "Bitte versuchen Sie es später erneut.",
                    color="negative",
                    position="top",
                    multi_line=True,
                )
            elif session.speech_enabled and reply:
                _speak_text(reply)
            refresh_ui()

        with ui.row().classes("w-full justify-end mt-2"):
            ui.button(
                "Senden", icon="send", on_click=_on_send
            ).props("unelevated").classes("bg-[#0f766e] text-white")


def _render_sidebar(session: BrowserSession, refresh_ui: Callable[[], None]) -> None:
    ctrl = session.primary_controller

    if session.current_patient is not None:
        with ui.card().classes("surface-card w-full shadow-none"):
            ui.label("Sitzung").classes("eyebrow")
            ui.label(_format_patient_name(session.current_patient)).classes(
                "text-xl font-semibold"
            )
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
                ui.button("Neu starten", on_click=lambda: _reset_browser_session(
                    session, refresh_ui
                )).props(
                    "outline"
                ).classes("grow")

    if (
        ctrl is not None
        and ctrl.state == DialogueState.ANAMNESIS
        and session.chat_phase_done
    ):
        _render_assistant_chat(session, refresh_ui)

    if ctrl is not None and session.current_patient is not None:
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
                    spo2 = session.simulated_oximeter.get("spo2")
                    pulse = session.simulated_oximeter.get("puls")
                    if spo2 is not None:
                        oximeter_text = f"SpO\u2082: {spo2}%, Puls: {pulse} bpm"
                    else:
                        oximeter_text = f"Puls: {pulse} bpm"
                    ui.label(oximeter_text).classes("text-sm text-slate-600 ml-2")

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
                    if not ctrl.summary.red_flags:
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
    controllers = session.controllers or ([session.controller] if session.controller else [])
    values = {
        "systolisch": session.simulated_bp["systolisch"],
        "diastolisch": session.simulated_bp["diastolisch"],
    }
    for controller in controllers:
        controller.record_vitals(values, "simuliert")
    if _check_live_form_escalation(
        session,
        controllers,
        {},
        refresh_ui,
        values,
    ):
        return
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
    controllers = session.controllers or ([session.controller] if session.controller else [])
    values = {"gewicht": session.simulated_weight["gewicht"]}
    for controller in controllers:
        controller.record_vitals(values, "simuliert")
    if _check_live_form_escalation(
        session,
        controllers,
        {},
        refresh_ui,
        values,
    ):
        return
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
    controllers = session.controllers or ([session.controller] if session.controller else [])
    values = {
        "spo2": session.simulated_oximeter["spo2"],
        "puls": session.simulated_oximeter["puls"],
    }
    for controller in controllers:
        controller.record_vitals(values, "simuliert")
    if _check_live_form_escalation(
        session,
        controllers,
        {},
        refresh_ui,
        values,
    ):
        return
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
