from typing import Callable

from app.dialogue.consent_flow import (
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_QUESTION,
    ROLE_EXPLANATION,
    is_consent_given,
)
from app.dialogue.state_machine import DialogueState, StateMachine
from app.devices.simulators import Simulator
from app.logger.audit_logger import (
    log_answer,
    log_escalation,
    log_info,
    log_red_flag,
    log_state_change,
)
from app.medical_rules.red_flag_engine import RedFlag, check
from app.output.export_json import export_summary
from app.output.summary_builder import AnamnesisSummary, build_summary
from app.patient_import.patient_schema import PatientRecord
from app.scenarios.chest_pain_scenario import (
    QUESTIONS as CHEST_PAIN_QUESTIONS,
    berechne_marburger_herzscore,
)
from app.scenarios.cough_scenario import QUESTIONS as COUGH_QUESTIONS
from app.scenarios.diabetes_scenario import (
    QUESTIONS as DIABETES_QUESTIONS,
    berechne_diabetes_verlaufsuebersicht,
    should_ask_follow_up,
)
from app.scenarios.hypertension_scenario import (
    QUESTIONS as HYPERTENSION_QUESTIONS,
    AnamnesisQuestion,
)

SCENARIO_MAP: dict[str, str] = {
    "A": "cough",
    "B": "chest_pain",
    "C": "hypertension",
    "D": "diabetes",
}


class DialogueController:
    def __init__(
        self,
        scenario_key: str,
        patient: PatientRecord,
        display_message: Callable[[str], None],
        request_input: Callable[[Callable[[str], None]], None],
    ) -> None:
        self._scenario_key = scenario_key
        self._scenario_id = SCENARIO_MAP.get(scenario_key, scenario_key)
        self._patient = patient
        self._display = display_message
        self._request_input = request_input

        self._state_machine = StateMachine()
        self._answers: dict[str, str] = {}
        self._vitals: dict[str, int | float] = {}
        self._red_flags: list[RedFlag] = []
        self._summary: AnamnesisSummary | None = None

        self._questions = self._load_questions()
        self._current_question_index = 0

    def _load_questions(self) -> list[AnamnesisQuestion]:
        if self._scenario_id == "cough":
            return list(COUGH_QUESTIONS)
        if self._scenario_id == "hypertension":
            return list(HYPERTENSION_QUESTIONS)
        if self._scenario_id == "chest_pain":
            return list(CHEST_PAIN_QUESTIONS)
        if self._scenario_id == "diabetes":
            return list(DIABETES_QUESTIONS)
        return []

    def start(self) -> None:
        log_info(f"Dialogue gestartet: Szenario={self._scenario_key}, Patient={self._patient.patient_id}")
        self._handle_state()

    def _handle_state(self) -> None:
        state = self._state_machine.state

        if state == DialogueState.EXPLAIN_ROLE:
            self._display(ROLE_EXPLANATION)
            self._state_machine.advance()
            self._handle_state()

        elif state == DialogueState.REQUEST_CONSENT:
            self._display(CONSENT_QUESTION)
            self._request_input(self._on_consent_answer)

        elif state == DialogueState.ANAMNESIS:
            self._ask_next_question()

        elif state == DialogueState.VITAL_PARAMETERS:
            self._measure_vitals()

        elif state == DialogueState.RED_FLAG_CHECK:
            self._check_red_flags()

        elif state == DialogueState.ESCALATION:
            self._show_escalation()

        elif state == DialogueState.SUMMARY:
            self._show_summary()

        elif state == DialogueState.HANDOVER:
            self._show_handover()

        elif state == DialogueState.END:
            pass

    def _on_consent_answer(self, answer: str) -> None:
        consent = is_consent_given(answer)
        if consent is None:
            self._display("Bitte antworten Sie mit 'ja' oder 'nein'.")
            self._request_input(self._on_consent_answer)
            return

        if not consent:
            log_info("Zustimmung abgelehnt - Anamnese wird nicht durchgefuehrt")
            self._display(CONSENT_DECLINED)
            self._state_machine.jump_to(DialogueState.END)
            self._handle_state()
            return

        log_info("Zustimmung erteilt - Anamnese beginnt")
        self._display(CONSENT_ACCEPTED)
        self._state_machine.advance()
        self._handle_state()

    def _ask_next_question(self) -> None:
        while self._current_question_index < len(self._questions):
            question = self._questions[self._current_question_index]
            if self._should_ask_question(question):
                self._display(f"\n{question.text}")
                self._request_input(self._on_anamnesis_answer)
                return

            self._answers[question.key] = ""
            self._current_question_index += 1

        self._state_machine.advance()
        self._handle_state()

    def _should_ask_question(self, question: AnamnesisQuestion) -> bool:
        if self._scenario_id != "diabetes":
            return True

        return should_ask_follow_up(question.key, self._answers)

    def _on_anamnesis_answer(self, answer: str) -> None:
        if answer.strip().lower() == "abbrechen":
            self._display("Die Anamnese wurde abgebrochen.")
            self._state_machine.jump_to(DialogueState.END)
            self._handle_state()
            return

        question = self._questions[self._current_question_index]

        if question.required and not answer.strip():
            self._display("Diese Angabe ist erforderlich. Bitte antworten Sie.")
            self._request_input(self._on_anamnesis_answer)
            return

        if question.input_type == "ja_nein":
            normalized = answer.strip().lower()
            if normalized not in ("ja", "j", "nein", "n", "yes", "no", "y"):
                self._display("Bitte antworten Sie mit 'ja' oder 'nein'.")
                self._request_input(self._on_anamnesis_answer)
                return
        elif question.input_type == "zahl":
            if not _is_number_or_unknown(answer):
                self._display("Bitte geben Sie eine Zahl ein.")
                self._request_input(self._on_anamnesis_answer)
                return

        self._answers[question.key] = answer.strip()
        log_answer(question.key, answer.strip())
        self._current_question_index += 1
        self._ask_next_question()

    def _measure_vitals(self) -> None:
        log_state_change("ANAMNESIS", "VITAL_PARAMETERS")
        self._display(
            "\nVitalparameter werden nun erfasst. "
            "Der Blutdruck wird ueber den Geraetesimulator gemessen..."
        )

        simulator = Simulator(geschlecht="weiblich", groesse_cm=167, alter=38)
        bp = simulator.blutdruck()
        self._vitals = {
            "systolisch": bp["systolisch"],
            "diastolisch": bp["diastolisch"],
        }

        log_info(f"Vitalparameter gemessen: {bp['systolisch']}/{bp['diastolisch']} mmHg (simuliert)")
        self._display(
            f"Simulierter Blutdruck: {bp['systolisch']}/{bp['diastolisch']} mmHg "
            f"[Quelle: Geraetesimulator]"
        )

        self._state_machine.advance()
        self._handle_state()

    def _check_red_flags(self) -> None:
        log_state_change("VITAL_PARAMETERS", "RED_FLAG_CHECK")
        self._red_flags = check(
            scenario=self._scenario_id,
            answers=self._answers,
            vitals=self._vitals,
        )

        if self._red_flags:
            for rf in self._red_flags:
                log_red_flag(rf.rule_id, rf.description, rf.severity)

            has_critical = any(rf.severity == "critical" for rf in self._red_flags)
            if has_critical:
                log_escalation(f"{len(self._red_flags)} Red Flag(s), davon critical")
                self._state_machine.jump_to(DialogueState.ESCALATION)
                self._handle_state()
                return

            self._display("\n--- WARNHINWEIS ---")
            for rf in self._red_flags:
                self._display(f"[{rf.rule_id}] {rf.description}")
            self._display("Hinweis: Aerztliche Pruefung empfohlen.")
            self._display("-------------------")
        else:
            log_info("Keine Red Flags ausgeloest")

        self._state_machine.advance()
        self._handle_state()

    def _show_escalation(self) -> None:
        self._display("\n========== ESKALATION ==========")
        self._display(
            "ACHTUNG: Es wurden kritische Warnzeichen erkannt. "
            "Eine sofortige aerztliche Uebernahme ist erforderlich!"
        )
        self._display("")
        for rf in self._red_flags:
            self._display(f"  [{rf.severity.upper()}] {rf.rule_id}: {rf.description}")
            self._display(f"    Ausgeloest durch: {rf.triggered_by}")
        self._display("")
        self._display(
            "Bitte informieren Sie umgehend das aerztliche Personal. "
            "Die Anamnese wird nicht als Routinefall fortgesetzt."
        )
        self._display("================================")

        self._build_and_export_summary()
        self._state_machine.advance()
        self._handle_state()

    def _show_summary(self) -> None:
        self._build_and_export_summary()

        self._display("\n--- Strukturierte Zusammenfassung ---")
        self._display(f"Patient: {self._summary.patient_name} ({self._summary.patient_id})")
        self._display(f"Szenario: {self._summary.scenario}")
        self._display(f"Zeitpunkt: {self._summary.timestamp}")
        self._display("")
        self._display("Anamnese-Antworten:")
        if self._summary.grouped_sections:
            for section, fields in self._summary.grouped_sections.items():
                self._display(f"  {section}:")
                for key, value in fields.items():
                    self._display(f"    {key}: {value or 'keine Angabe'}")
        else:
            for key, value in self._summary.answers.items():
                self._display(f"  {key}: {value}")
        self._display("")
        self._display(f"Vitalparameter ({self._summary.vitals_source}):")
        for key, value in self._summary.vitals.items():
            self._display(f"  {key}: {value}")

        if self._scenario_id == "chest_pain":
            self._display_herzscore()
        if self._scenario_id == "diabetes":
            self._display_diabetes_verlaufsuebersicht()

        if self._summary.red_flags:
            self._display("")
            self._display("Red Flags:")
            for rf in self._summary.red_flags:
                self._display(f"  [{rf.severity}] {rf.description}")

        if self._summary.open_points:
            self._display("")
            self._display("Offene Punkte:")
            for point in self._summary.open_points:
                self._display(f"  - {point}")

        self._display("")
        self._display("[SYNTHETISCHE DATEN - Kein realer Patient]")
        self._display("------------------------------------")

        self._state_machine.advance()
        self._handle_state()

    def _display_herzscore(self) -> None:
        result = berechne_marburger_herzscore(self._answers)
        self._display("")
        self._display("Marburger Herzscore (nur zur Dokumentation):")
        self._display(f"  Score: {result['score']} / {result['max_score']}")
        self._display(f"  Kriterien: {result['details']}")
        self._display(f"  Einordnung: {result['einordnung']}")
        self._display(f"  Hinweis: {result['hinweis']}")

    def _display_diabetes_verlaufsuebersicht(self) -> None:
        result = berechne_diabetes_verlaufsuebersicht(self._answers, self._vitals)
        self._display("")
        self._display("Diabetes-Verlaufsuebersicht (nur zur Dokumentation):")
        self._display(f"  Verlauf: {result['verlauf']}")
        self._display(f"  Aktuelle Symptome: {result['symptome']}")
        self._display(f"  Komplikationen: {result['komplikationen']}")
        self._display(f"  Vorbefunde: {result['vorbefunde']}")
        self._display(f"  Hinweis: {result['hinweis']}")

    def _show_handover(self) -> None:
        self._display(
            "\nDie Zusammenfassung wurde fuer das aerztliche Personal erstellt. "
            "Die Uebergabe ist abgeschlossen."
        )
        self._display("Vielen Dank fuer Ihre Angaben. Sie koennen das System nun schliessen.")
        self._state_machine.advance()

    def _build_and_export_summary(self) -> None:
        if self._summary is not None:
            return

        self._summary = build_summary(
            patient=self._patient,
            scenario=self._scenario_key,
            answers=self._answers,
            vitals=self._vitals,
            vitals_source="simuliert",
            red_flags=self._red_flags,
        )

        filepath = export_summary(self._summary)
        log_info(f"Export gespeichert: {filepath}")
        self._display(f"\n[Export gespeichert: {filepath}]")


def _is_number_or_unknown(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "unbekannt":
        return True

    try:
        float(value.strip().replace(",", "."))
        return True
    except ValueError:
        return False
