import re
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
ADDITIONAL_MEDICATIONS_KEY = "weitere_medikamente"

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


def _risikofaktor_frage(rf: str) -> str | None:
    rf_lower = rf.lower()
    name = rf.split(":", 1)[0].strip().lower()
    wert = rf.split(":", 1)[1].strip() if ":" in rf else ""

    if name.startswith("rauchen"):
        if wert.lower() in ("ja", "aktiv"):
            return "Rauchen Sie weiterhin?"
        return "Rauchen Sie?"

    if name.startswith("alkohol"):
        if wert.lower() in ("ja", "aktiv"):
            return "Trinken Sie weiterhin regelmäßig Alkohol?"
        return "Trinken Sie regelmäßig Alkohol?"

    if name.startswith("bmi"):
        return None

    return f"Besteht {rf} weiterhin?"


class DialogueController:
    def __init__(
        self,
        scenario_key: str,
        patient: PatientRecord,
        display_message: Callable[[str], None],
        request_input: Callable[[Callable[[str], None]], None],
        defer_anamnesis: bool = False,
    ) -> None:
        self._scenario_key = scenario_key
        self._scenario_id = SCENARIO_MAP.get(scenario_key, scenario_key)
        self._patient = patient
        self._display = display_message
        self._request_input = request_input
        # Wenn True, werden die Anamnese-Fragen beim Eintritt in den
        # ANAMNESIS-Zustand NICHT automatisch gestellt. Stattdessen startet
        # die Weboberflaeche sie nach dem KI-Vorab-Chat ueber begin_anamnesis().
        self._defer_anamnesis = defer_anamnesis

        self._state_machine = StateMachine()
        self._answers: dict[str, str] = {}
        self._vitals: dict[str, int | float] = {}
        self._vital_sources: dict[str, str] = {}
        self._vitals_source = "nicht erhoben"
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

        detail_map: dict[str, str] = {}
        for med_name in self._patient.medications:
            name_lower = med_name.lower()
            for detail in self._patient.details.medication_details:
                if name_lower in detail.lower():
                    detail_map[med_name] = detail
                    break
            else:
                detail_map[med_name] = med_name

        for idx, med_name in enumerate(self._patient.medications):
            med_text = detail_map[med_name]
            questions.append(
                AnamnesisQuestion(
                    key=f"{MED_PREFIX}{idx}",
                    text=f"Nehmen Sie {med_text} so ein, wie es Ihnen verschrieben wurde?",
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
        questions.append(
            AnamnesisQuestion(
                key=ADDITIONAL_MEDICATIONS_KEY,
                text=(
                    "Nehmen Sie weitere Medikamente, die nicht in Ihrer Akte stehen? "
                    "Denken Sie auch an frei gekaufte Mittel und Medikamente, die Sie "
                    "nur gelegentlich oder wegen Ihrer aktuellen Beschwerden genommen "
                    "haben. Bitte nennen Sie Name, Häufigkeit und Grund oder schreiben Sie 'keine'."
                ),
                input_type="freitext",
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
        scenario_map: dict[str, list[AnamnesisQuestion]] = {
            "cough": list(COUGH_QUESTIONS),
            "hypertension": list(HYPERTENSION_QUESTIONS),
            "chest_pain": list(CHEST_PAIN_QUESTIONS),
            "diabetes": list(DIABETES_QUESTIONS),
        }
        scenario_qs = scenario_map.get(self._scenario_id, [])

        # Keys aus Szenario-Definitionen, die durch Akten-Daten ersetzt werden
        akten_keys = frozenset({
            "vorerkrankungen", "risikofaktoren",
            "kardiovaskulaere_risikofaktoren", "bekannte_diagnosen",
        })
        hat_akten_daten = bool(
            self._patient.details.long_term_diagnoses
            or self._patient.details.risk_factors
            or (self._patient.conditions or "").strip()
        )

        questions: list[AnamnesisQuestion] = []

        # 1. Erste Frage des Szenarios
        if scenario_qs:
            questions.append(scenario_qs[0])

        # 2. Vorerkrankungen & Risikofaktoren aus der Akte (Position 2)
        if hat_akten_daten:
            questions.extend(self._conditions_questions)

        # 3. Restliche Szenario-Fragen (überspringe alte vorerkrankungen/risikofaktoren,
        #    wenn Akten-Daten vorhanden sind)
        for q in scenario_qs[1:]:
            if hat_akten_daten and q.key in akten_keys:
                continue
            questions.append(q)

        # 4. Medikamenten-Fragen
        if self._patient.medications:
            questions.extend(self._medication_questions)
        else:
            questions.append(
                AnamnesisQuestion(
                    key="medikamente",
                    text=(
                        "Welche Medikamente nehmen Sie? Denken Sie auch an frei gekaufte "
                        "Mittel und Medikamente, die Sie nur gelegentlich oder wegen Ihrer "
                        "aktuellen Beschwerden genommen haben. Bitte nennen Sie Name, "
                        "Häufigkeit und Grund oder schreiben Sie 'keine'."
                    ),
                    input_type="freitext",
                )
            )
        return questions

    @property
    def _conditions_questions(self) -> list[AnamnesisQuestion]:
        questions: list[AnamnesisQuestion] = []
        diagnoses = self._patient.details.long_term_diagnoses
        risk_factors = self._patient.details.risk_factors
        conditions_str = (self._patient.conditions or "").strip()

        if not diagnoses and not risk_factors:
            if conditions_str:
                questions.append(
                    AnamnesisQuestion(
                        key="vorerkrankungen_aktuell",
                        text=(
                            f"In Ihrer Akte sind folgende Vorerkrankungen und Risikofaktoren "
                            f"vermerkt: {conditions_str}. Hat sich daran etwas "
                            f"verändert? Sind Erkrankungen hinzugekommen oder wurden "
                            f"Beschwerden in letzter Zeit schlimmer oder besser? "
                            f"Bitte beschreiben Sie."
                        ),
                        input_type="freitext",
                        required=False,
                    )
                )
            return questions

        if diagnoses:
            diagnose_liste = "\n".join(f"  • {d}" for d in diagnoses)
            questions.append(
                AnamnesisQuestion(
                    key="vorerkrankungen_liste",
                    text=(
                        f"In Ihrer Akte sind folgende Vorerkrankungen vermerkt:\n"
                        f"{diagnose_liste}\n\n"
                        f"Hat sich an Ihren Vorerkrankungen etwas verändert? "
                        f"Sind Erkrankungen hinzugekommen oder wurden "
                        f"Beschwerden in letzter Zeit schlimmer oder besser? "
                        f"Bitte beschreiben Sie."
                    ),
                    input_type="freitext",
                    required=False,
                )
            )

        for idx, rf in enumerate(risk_factors):
            if rf.lower().startswith("familien"):
                continue

            # Im Diabetes-Szenario werden Rauchen und Alkohol bereits als
            # feste, verständliche Fragen mit passenden Folgefragen erhoben.
            # Aktenbasierte Risikofragen würden diese Angaben verdoppeln.
            if self._scenario_id == "diabetes" and rf.lower().startswith(("rauchen", "alkohol")):
                continue

            text = _risikofaktor_frage(rf)
            if text is None:
                continue

            questions.append(
                AnamnesisQuestion(
                    key=f"risikofaktor_{idx}",
                    text=text,
                    input_type="ja_nein",
                    required=True,
                )
            )

        return questions

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
            # Im aufgeschobenen Modus wartet die Anamnese auf den KI-Vorab-Chat.
            # begin_anamnesis() stoesst die Fragen spaeter an.
            if self._defer_anamnesis:
                return
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

    def begin_anamnesis(self, prefilled: dict[str, str] | None = None) -> None:
        """Startet die Anamnese-Fragen nach dem KI-Vorab-Chat.

        Bereits durch die KI extrahierte, gueltige Antworten werden uebernommen
        und im Schritt-fuer-Schritt-Dialog uebersprungen. Loest die Anamnese aus
        dem aufgeschobenen Zustand (siehe defer_anamnesis).
        """
        self._defer_anamnesis = False

        if self.state != DialogueState.ANAMNESIS:
            return

        if prefilled:
            question_keys = {q.key for q in self._questions}
            for question in self._questions:
                value = str(prefilled.get(question.key, "")).strip()
                if question.key in question_keys and value and self._is_valid_answer(
                    question, value
                ):
                    self._answers[question.key] = value

        # KI-Antworten koennen bereits ein kritisches Warnzeichen enthalten.
        if self._escalate_critical_acute_answers():
            return

        self._ask_next_question()

    def _is_valid_answer(self, question: AnamnesisQuestion, value: str) -> bool:
        """Prueft, ob ein (z. B. von der KI gelieferter) Wert zum Fragetyp passt."""
        normalized = value.strip().lower()
        if question.input_type == "ja_nein":
            return normalized in ("ja", "j", "nein", "n", "yes", "no", "y")
        if question.input_type == "zahl":
            return _is_number_or_unknown(value)
        return bool(value.strip())

    def _ask_next_question(self) -> None:
        while self._current_question_index < len(self._questions):
            question = self._questions[self._current_question_index]
            if self._should_ask_question(question):
                # Bereits gueltig vorausgefuellte Fragen (KI) im Dialog
                # ueberspringen, statt sie erneut zu stellen.
                existing = (self._answers.get(question.key) or "").strip()
                if existing and self._is_valid_answer(question, existing):
                    self._asked_question_count += 1
                    self._current_question_index += 1
                    continue

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
            follow_ups = {
                "auswurf_farbe": "auswurf",
                "korpertemperatur": "fieber",
                "ruhedyspnoe": "dyspnoe",
                "sprechen_beeintraechtigt": "dyspnoe",
                "atemabhaengige_schmerzen": "thorakale_schmerzen",
            }
            parent_key = follow_ups.get(question_key)
            if parent_key:
                parent_answer = (answers.get(parent_key) or "").strip().lower()
                return parent_answer in ("ja", "j", "yes", "y")
            return True

        if self._scenario_id == "diabetes":
            return should_ask_follow_up(question_key, answers)

        if self._scenario_id == "chest_pain":
            if question_key == "ruhedyspnoe":
                return (answers.get("atemnot") or "").strip().lower() in (
                    "ja", "j", "yes", "y",
                )
            return True

        if self._scenario_id == "hypertension":
            bekannte_hypertonie = (answers.get("bluthochdruck_bekannt") or "").strip().lower()
            kontroll_fragen = {
                "letzte_kontrolle", "behandlung_geaendert",
                "heimwerte_vorhanden", "heimwerte_verlauf",
            }
            erstauffaellig_fragen = {
                "auffaelliger_wert_wann", "mehrfach_gemessen",
                "fruehere_auffaellige_werte",
            }
            if question_key in kontroll_fragen:
                if bekannte_hypertonie not in ("ja", "j", "yes", "y"):
                    return False
                if question_key == "heimwerte_verlauf":
                    return (answers.get("heimwerte_vorhanden") or "").strip().lower() in (
                        "ja", "j", "yes", "y",
                    )
                return True
            if question_key in erstauffaellig_fragen:
                return bekannte_hypertonie in ("nein", "n", "no")
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

        if self._escalate_critical_acute_answers():
            return

        self._ask_next_question()

    def submit_mass_anamnesis(
        self,
        answers: dict[str, str],
        vital_sources: dict[str, str] | None = None,
    ) -> None:
        if vital_sources is not None:
            self._vital_sources = dict(vital_sources)
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

        if self._escalate_critical_acute_answers():
            return

        self._state_machine.advance()
        self._handle_state()

    def _measure_vitals(self) -> None:
        log_state_change("ANAMNESIS", "VITAL_PARAMETERS")

        if self._scenario_id == "cough":
            self._measure_cough_vitals()
            self._state_machine.advance()
            self._handle_state()
            return

        sys_str = (self._answers.get("blutdruck_systolisch") or "").strip()
        dia_str = (self._answers.get("blutdruck_diastolisch") or "").strip()
        puls_str = (self._answers.get("puls") or "").strip()

        bp_known = (
            sys_str.lower() not in ("", "unbekannt")
            and dia_str.lower() not in ("", "unbekannt")
        )

        if bp_known:
            self._vitals.update({
                "systolisch": float(sys_str.replace(",", ".")),
                "diastolisch": float(dia_str.replace(",", ".")),
            })
            self._vital_sources.setdefault("systolisch", "manuell eingegeben")
            self._vital_sources.setdefault("diastolisch", "manuell eingegeben")
            self._display(
                f"Blutdruck aus Anamnese übernommen: "
                f"{self._vitals['systolisch']}/{self._vitals['diastolisch']} mmHg"
            )
        if puls_str.lower() not in ("", "unbekannt"):
            self._vitals["puls"] = float(puls_str.replace(",", "."))
            self._vital_sources.setdefault("puls", "manuell eingegeben")

        gewicht_key = "gewicht_aktuell" if self._scenario_id == "diabetes" else "gewicht"
        gewicht_str = (self._answers.get(gewicht_key) or "").strip()
        if gewicht_str.lower() not in ("", "unbekannt"):
            self._vitals["gewicht"] = float(gewicht_str.replace(",", "."))
            self._vital_sources.setdefault("gewicht", "manuell eingegeben")

        self._refresh_vitals_source()

        self._state_machine.advance()
        self._handle_state()

    def _measure_cough_vitals(self) -> None:
        # Bereits bewusst über die UI übernommene Geräte-/Simulatorwerte bleiben
        # erhalten. Die Anamnese ergänzt nur manuell angegebene Werte.

        temperatur = _extract_number(self._answers.get("korpertemperatur", ""))
        if temperatur is not None:
            self._vitals["temperatur"] = temperatur
            self._vital_sources.setdefault("temperatur", "manuell eingegeben")

        atemfrequenz = _extract_number(self._answers.get("atemfrequenz", ""))
        if atemfrequenz is not None:
            self._vitals["atemfrequenz"] = atemfrequenz
            self._vital_sources.setdefault("atemfrequenz", "manuell eingegeben")

        self._refresh_vitals_source()

    def record_vitals(
        self,
        values: dict[str, int | float],
        source: str,
    ) -> None:
        """Übernimmt Messwerte samt Herkunft, ohne die Zahlenstruktur zu verändern."""
        self._vitals.update(values)
        for key in values:
            self._vital_sources[key] = source
        self._refresh_vitals_source()

    def _refresh_vitals_source(self) -> None:
        sources = list(dict.fromkeys(self._vital_sources.values()))
        if not sources:
            self._vitals_source = "nicht erhoben"
        elif len(sources) == 1:
            self._vitals_source = sources[0]
        else:
            self._vitals_source = ", ".join(sources)

    def _escalate_critical_acute_answers(self) -> bool:
        return self.check_partial_answers_for_escalation(self._answers, self._vitals)

    def check_partial_answers_for_escalation(
        self,
        answers: dict[str, str],
        vitals: dict[str, int | float] | None = None,
    ) -> bool:
        """Prüft unvollständige Eingaben und stoppt bei kritischen Warnzeichen.

        Diese Methode wird sowohl vom schrittweisen Dialog als auch von der
        Weboberfläche nach einzelnen Eingaben und Gerätemessungen verwendet.
        Fehlende Pflichtangaben sind bei dieser Zwischenprüfung ausdrücklich
        erlaubt.
        """
        if self.state != DialogueState.ANAMNESIS:
            return False

        question_keys = {question.key for question in self._questions}
        for key, value in answers.items():
            if key in question_keys:
                self._answers[key] = str(value).strip()
        if vitals:
            self._vitals.update(vitals)

        flags = self.preview_partial_red_flags(answers, vitals)
        if not any(flag.severity == "critical" for flag in flags):
            return False

        self._red_flags = flags
        for flag in flags:
            log_red_flag(flag.rule_id, flag.description, flag.severity)
        log_escalation(
            f"Kritisches Warnzeichen während der {self._scenario_id}-Anamnese"
        )
        self._state_machine.jump_to(DialogueState.ESCALATION)
        self._handle_state()
        return True

    def preview_partial_red_flags(
        self,
        answers: dict[str, str],
        vitals: dict[str, int | float] | None = None,
    ) -> list[RedFlag]:
        """Prüft Zwischenwerte, ohne Antworten oder Dialogzustand zu verändern."""
        candidate_answers = dict(self._answers)
        question_keys = {question.key for question in self._questions}
        candidate_answers.update(
            {
                key: str(value).strip()
                for key, value in answers.items()
                if key in question_keys
            }
        )
        candidate_vitals = dict(self._vitals)
        if vitals:
            candidate_vitals.update(vitals)

        return check(
            scenario=self._scenario_id,
            answers=candidate_answers,
            vitals=candidate_vitals,
            patient_medications=self._patient.medications,
        )

    def _escalate_critical_cough_answers(self) -> bool:
        """Kompatibilität für bestehende Aufrufer der früheren Husten-Methode."""
        if self._scenario_id != "cough":
            return False
        return self._escalate_critical_acute_answers()

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
            "Bitte sofort dem Praxisteam melden. "
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
        result = berechne_marburger_herzscore(
            self._answers,
            alter=_calculate_age(self._patient.date_of_birth),
            geschlecht=self._patient.details.gender,
        )
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

    def update_answers_and_regenerate(
        self,
        answers: dict[str, str],
        vital_sources: dict[str, str] | None = None,
    ) -> None:
        if vital_sources is not None:
            self._vital_sources.update(vital_sources)
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
            vitals_source=self._vitals_source,
            vital_sources=self._vital_sources,
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


def _extract_number(value: str) -> float | None:
    match = re.search(r"\d+(?:[.,]\d+)?", value)
    if not match:
        return None
    return float(match.group(0).replace(",", "."))
