from datetime import date
from pathlib import Path
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
from app.medical_rules.scenario_recommendation import recommend_scenario
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

MED_PREFIX = "med_adhaerenz_"
MED_REASON_PREFIX = "med_adhaerenz_grund_"

SCENARIO_MAP: dict[str, str] = {
    "A": "cough",
    "B": "chest_pain",
    "C": "hypertension",
    "D": "diabetes",
}


def _calculate_age(dob_str: str) -> int:
    try:
        born = date.fromisoformat(dob_str)
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except (ValueError, TypeError):
        return 38


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
        self._export_path: Path | None = None

        self._questions = self._load_questions()
        self._current_question_index = 0
        self._asked_question_count = 0

    @property
    def state(self) -> DialogueState:
        return self._state_machine.state

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    @property
    def summary(self) -> AnamnesisSummary | None:
        return self._summary

    @property
    def export_path(self) -> Path | None:
        return self._export_path

    @property
    def _medication_questions(self) -> list[AnamnesisQuestion]:
        questions: list[AnamnesisQuestion] = []
        for idx, med_name in enumerate(self._patient.medications):
            questions.append(
                AnamnesisQuestion(
                    key=f"{MED_PREFIX}{idx}",
                    text=f"Nehmen Sie {med_name} regelmäßig/wie verschrieben ein?",
                    input_type="ja_nein",
                )
            )
            questions.append(
                AnamnesisQuestion(
                    key=f"{MED_REASON_PREFIX}{idx}",
                    text="Warum nicht?",
                    input_type="freitext",
                    required=False,
                )
            )
        return questions

    @property
    def current_question(self) -> AnamnesisQuestion | None:
        if self._current_question_index < len(self._questions):
            return self._questions[self._current_question_index]
        return None

    @property
    def asked_question_count(self) -> int:
        return self._asked_question_count

    @property
    def question_progress(self) -> tuple[int, int]:
        if self.state != DialogueState.ANAMNESIS:
            return self._asked_question_count, max(self._asked_question_count, 1)

        remaining_questions = sum(
            1
            for question in self._questions[self._current_question_index :]
            if self._should_ask_question(question)
        )
        total_questions = max(
            (self._asked_question_count - 1) + remaining_questions,
            1,
        )
        return self._asked_question_count, total_questions

    @staticmethod
    def get_recommended_scenario(patient: PatientRecord) -> str | None:
        return recommend_scenario(patient)

    @property
    def phase_label(self) -> str:
        phase_labels = {
            DialogueState.EXPLAIN_ROLE: "Rollenerklaerung",
            DialogueState.REQUEST_CONSENT: "Einwilligung",
            DialogueState.ANAMNESIS: "Assistierte Anamnese",
            DialogueState.VITAL_PARAMETERS: "Vitalparameter",
            DialogueState.RED_FLAG_CHECK: "Risikoprüfung",
            DialogueState.ESCALATION: "Eskalation",
            DialogueState.SUMMARY: "Zusammenfassung",
            DialogueState.HANDOVER: "Übergabe",
            DialogueState.END: "Abschluss",
        }
        return phase_labels[self.state]

    def _load_questions(self) -> list[AnamnesisQuestion]:
        questions: list[AnamnesisQuestion] = []
        if self._conditions_question:
            questions.append(self._conditions_question)
        if self._scenario_id == "cough":
            questions.extend(COUGH_QUESTIONS)
        elif self._scenario_id == "hypertension":
            questions.extend(HYPERTENSION_QUESTIONS)
        elif self._scenario_id == "chest_pain":
            questions.extend(CHEST_PAIN_QUESTIONS)
        elif self._scenario_id == "diabetes":
            questions.extend(DIABETES_QUESTIONS)
        if self._patient.medications:
            questions.extend(self._medication_questions)
        else:
            questions.append(
                AnamnesisQuestion(
                    key="medikamente",
                    text="Welche Medikamente nehmen Sie regelmäßig ein?",
                    input_type="freitext",
                )
            )
        return questions

    @property
    def _conditions_question(self) -> AnamnesisQuestion | None:
        if not self._patient.conditions:
            return None
        return AnamnesisQuestion(
            key="vorerkrankungen_aktuell",
            text=(
                f"In Ihrer Akte sind folgende Vorerkrankungen und Risikofaktoren "
                f"vermerkt: {self._patient.conditions}. Hat sich daran etwas "
                f"verändert? Sind Erkrankungen hinzugekommen oder wurden "
                f"Beschwerden in letzter Zeit schlimmer oder besser? "
                f"Bitte beschreiben Sie."
            ),
            input_type="freitext",
            required=False,
        )

    def start(self) -> None:
        log_info(f"Dialogue gestartet: Szenario={self._scenario_key}, Patient={self._patient.patient_id}")
        self._handle_state()

    def _handle_state(self) -> None:
        state = self._state_machine.state

        if state == DialogueState.EXPLAIN_ROLE:
            self._state_machine.advance()
            self._handle_state()

        elif state == DialogueState.REQUEST_CONSENT:
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
            log_info("Zustimmung abgelehnt - Anamnese wird nicht durchgeführt")
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
                self._asked_question_count += 1
                self._display(f"\n{question.text}")
                self._request_input(self._on_anamnesis_answer)
                return

            self._answers[question.key] = ""
            self._current_question_index += 1

        self._state_machine.advance()
        self._handle_state()

    def is_question_visible(self, question_key: str, answers: dict[str, str] | None = None) -> bool:
        if answers is None:
            answers = self._answers

        # Medikamenten-Grund-Frage nur zeigen, wenn die Adhärenz-Frage mit "nein" beantwortet wurde
        if question_key.startswith(MED_REASON_PREFIX):
            idx = question_key[len(MED_REASON_PREFIX):]
            adhaerenz_key = f"{MED_PREFIX}{idx}"
            return (answers.get(adhaerenz_key) or "").strip().lower() in ("nein", "n", "no")

        if self._scenario_id == "cough":
            if question_key == "korpertemperatur":
                fieber_antwort = (answers.get("fieber") or "").strip().lower()
                return fieber_antwort in ("ja", "j", "yes", "y")
            return True

        if self._scenario_id == "diabetes":
            return should_ask_follow_up(question_key, answers)

        if self._scenario_id == "hypertension":
            if question_key == "puls_messen":
                antwort = (answers.get("puls") or "").strip().lower()
                return antwort == "unbekannt"
            if question_key == "blutdruck_messen":
                antwort = (answers.get("blutdruck_systolisch") or "").strip().lower()
                return antwort == "unbekannt"
            if question_key == "gewicht_messen":
                antwort = (answers.get("gewicht") or "").strip().lower()
                return antwort == "unbekannt"
            return True

        return True

    def get_patient(self) -> PatientRecord:
        return self._patient

    def _should_ask_question(self, question: AnamnesisQuestion) -> bool:
        return self.is_question_visible(question.key)

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

    def submit_mass_anamnesis(self, answers: dict[str, str]) -> None:
        for q in self._questions:
            value = answers.get(q.key, "").strip()
            if q.required and self.is_question_visible(q.key, answers) and not value:
                raise ValueError(
                    f"Die Frage '{q.text}' ist erforderlich."
                )
            self._answers[q.key] = value

        self._current_question_index = len(self._questions)
        self._asked_question_count = sum(
            1 for q in self._questions
            if self.is_question_visible(q.key, self._answers)
        )

        self._state_machine.advance()
        self._handle_state()

    def _measure_vitals(self) -> None:
        log_state_change("ANAMNESIS", "VITAL_PARAMETERS")

        sys_str = (self._answers.get("blutdruck_systolisch") or "").strip()
        dia_str = (self._answers.get("blutdruck_diastolisch") or "").strip()
        puls_str = (self._answers.get("puls") or "").strip()

        bp_known = (
            sys_str.lower() not in ("", "unbekannt")
            and dia_str.lower() not in ("", "unbekannt")
        )

        if bp_known:
            self._vitals = {
                "systolisch": float(sys_str.replace(",", ".")),
                "diastolisch": float(dia_str.replace(",", ".")),
            }
            self._display(
                f"Blutdruck aus Anamnese übernommen: "
                f"{self._vitals['systolisch']}/{self._vitals['diastolisch']} mmHg"
            )
        else:
            simulator = Simulator(geschlecht="weiblich", groesse_cm=167, alter=38)
            bp = simulator.blutdruck()
            self._vitals = {
                "systolisch": bp["systolisch"],
                "diastolisch": bp["diastolisch"],
            }
            log_info(
                f"Vitalparameter simuliert: {bp['systolisch']}/{bp['diastolisch']} mmHg"
            )
            self._display(
                f"Simulierter Blutdruck: {bp['systolisch']}/{bp['diastolisch']} mmHg "
                f"[Quelle: Gerätesimulator]"
            )

        if puls_str.lower() not in ("", "unbekannt"):
            self._vitals["puls"] = float(puls_str.replace(",", "."))

        gewicht_str = (self._answers.get("gewicht") or "").strip()
        if gewicht_str.lower() not in ("", "unbekannt"):
            self._vitals["gewicht"] = float(gewicht_str.replace(",", "."))
        else:
            sim = Simulator(
                geschlecht=self._patient.details.gender,
                groesse_cm=self._patient.details.groesse_cm,
                alter=_calculate_age(self._patient.date_of_birth),
            )
            sim_gewicht = sim.gewicht()
            self._vitals["gewicht"] = sim_gewicht["gewicht"]
            log_info(
                f"Gewicht simuliert: {sim_gewicht['gewicht']} kg "
                f"(BMI: {sim_gewicht['bmi']}, {sim_gewicht['klasse']})"
            )
            self._display(
                f"Simuliertes Gewicht: {sim_gewicht['gewicht']} kg "
                f"(BMI: {sim_gewicht['bmi']}, {sim_gewicht['klasse']})"
            )

        self._state_machine.advance()
        self._handle_state()

    def _check_red_flags(self) -> None:
        log_state_change("VITAL_PARAMETERS", "RED_FLAG_CHECK")
        self._red_flags = check(
            scenario=self._scenario_id,
            answers=self._answers,
            vitals=self._vitals,
            patient_medications=self._patient.medications,
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
            self._display("Hinweis: Ärztliche Prüfung empfohlen.")
            self._display("-------------------")
        else:
            log_info("Keine Red Flags ausgeloest")

        self._state_machine.advance()
        self._handle_state()

    def _show_escalation(self) -> None:
        self._display("\n========== ESKALATION ==========")
        self._display(
            "ACHTUNG: Es wurden kritische Warnzeichen erkannt. "
            "Eine sofortige ärztliche Übernahme ist erforderlich!"
        )
        self._display("")
        for rf in self._red_flags:
            self._display(f"  [{rf.severity.upper()}] {rf.rule_id}: {rf.description}")
            self._display(f"    Ausgelöst durch: {rf.triggered_by}")
        self._display("")
        self._display(
            "Bitte informieren Sie umgehend das ärztliche Personal. "
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
            "\nDie Zusammenfassung wurde für das ärztliche Personal erstellt. "
            "Die Übergabe ist abgeschlossen."
        )
        self._display("Vielen Dank fuer Ihre Angaben. Sie koennen das System nun schliessen.")
        self._state_machine.advance()

    def get_questions_with_answers(self) -> list[tuple]:
        return [
            (q, self._answers.get(q.key, ""))
            for q in self._questions
        ]

    def update_answers_and_regenerate(self, answers: dict[str, str]) -> None:
        for q in self._questions:
            value = answers.get(q.key, "").strip()
            if q.required and not value:
                raise ValueError(
                    f"Die Frage '{q.text}' ist erforderlich."
                )
            self._answers[q.key] = value

        self._red_flags = check(
            scenario=self._scenario_id,
            answers=self._answers,
            vitals=self._vitals,
            patient_medications=self._patient.medications,
        )

        self._summary = None
        self._build_and_export_summary()

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

        self._export_path = export_summary(self._summary)
        log_info(f"Export gespeichert: {self._export_path}")
        self._display(f"\n[Export gespeichert: {self._export_path}]")


def _is_number_or_unknown(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "unbekannt":
        return True

    try:
        float(value.strip().replace(",", "."))
        return True
    except ValueError:
        return False
