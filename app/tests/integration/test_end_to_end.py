"""Integrationstests: 3 geforderte End-to-End-Faelle.

1. Unkritischer Routinefall ohne Red Flag
2. Fall mit Red Flag und Eskalationshinweis
3. Fall mit Geraete-/Eingabefehler (Abbruch durch Patient)
"""

from unittest.mock import patch

from app.dialogue.dialogue_controller import DialogueController
from app.dialogue.state_machine import DialogueState
from app.patient_import.patient_schema import PatientRecord


def _make_patient() -> PatientRecord:
    return PatientRecord(
        patient_id="P-INT-001",
        first_name="Erika",
        last_name="Mustermann",
        date_of_birth="1975-04-22",
    )


class TestRoutineCaseNoRedFlag:
    """Fall 1: Hypertonie-Kontrolle ohne kritische Werte."""

    def test_full_routine_dialogue(self) -> None:
        messages: list[str] = []
        callbacks: list = []

        controller = DialogueController(
            scenario_key="C",
            patient=_make_patient(),
            display_message=lambda text: messages.append(text),
            request_input=lambda cb: callbacks.append(cb),
        )

        controller.start()
        assert controller.state == DialogueState.REQUEST_CONSENT

        # Consent geben
        callbacks.pop()("ja")
        assert controller.state == DialogueState.ANAMNESIS

        # Alle Hypertonie-Fragen mit unkritischen Werten beantworten
        routine_answers = [
            "130",           # systolisch
            "80",            # diastolisch
            "72",            # puls
            "Ruhend, sitzend",  # messbedingungen
            "nein",          # kopfschmerz
            "nein",          # brustschmerz
            "nein",          # atemnot
            "nein",          # neurologische_symptome
            "nein",          # sehstoerungen
            "Keine",         # vorerkrankungen
            "Wenig Sport",   # lebensstil
            "nein",          # risikofaktoren
            "78",            # gewicht
            "ASS 100 mg",    # medikamente
        ]

        for answer in routine_answers:
            if callbacks:
                callbacks.pop()(answer)

        # Nach normalen Vitalparametern (simuliert) sollte kein Red Flag ausloesen
        # Controller sollte bis END kommen
        assert controller.state == DialogueState.END
        assert controller.summary is not None
        assert controller.summary.escalation_required is False
        assert controller.summary.red_flags == [] or all(
            rf.severity == "warning" for rf in controller.summary.red_flags
        )


class TestRedFlagEscalation:
    """Fall 2: Brustschmerz mit kritischen Symptomen -> Eskalation."""

    def test_critical_chest_pain_escalates(self) -> None:
        messages: list[str] = []
        callbacks: list = []

        controller = DialogueController(
            scenario_key="B",
            patient=_make_patient(),
            display_message=lambda text: messages.append(text),
            request_input=lambda cb: callbacks.append(cb),
        )

        controller.start()
        callbacks.pop()("ja")  # consent

        # Brustschmerz hat 17 Fragen + 1 medikamente-Frage (keine Medis hinterlegt): 18
        critical_answers = [
            "Hinter dem Brustbein",  # lokalisation
            "vor 30 Minuten",        # beginn
            "Seit 30 Minuten",       # dauer
            "drückend",              # schmerzcharakter
            "linker Arm",            # ausstrahlung -> RF!
            "ja",                    # belastungsabhaengigkeit -> RF!
            "ja",                    # ruhe_besserung
            "ja",                    # atemnot -> RF!
            "ja",                    # uebelkeit
            "ja",                    # kaltschweissigkeit -> RF!
            "nein",                  # synkope
            "nein",                  # ausgepraege_schwaeche
            "nein",                  # bekannte_khk
            "nein",                  # alter_ueber_55
            "Bluthochdruck",         # kardiovaskulaere_risikofaktoren
            "Keine",                 # vorerkrankungen
            "nein",                  # druckschmerz_thoraxwand
            "ASS 100 mg",            # medikamente
        ]

        for answer in critical_answers:
            if callbacks:
                callbacks.pop()(answer)

        # Soll in ESCALATION oder END landen (nach Eskalation -> END)
        assert controller.state == DialogueState.END
        assert controller.summary is not None
        assert controller.summary.escalation_required is True
        assert any(rf.severity == "critical" for rf in controller.summary.red_flags)

        # Eskalations-Meldung muss ausgegeben worden sein
        all_text = " ".join(messages)
        assert "ESKALATION" in all_text or "sofortige" in all_text.lower()

    def test_cough_warning_interrupts_dialogue_immediately(self) -> None:
        messages: list[str] = []
        callbacks: list = []
        controller = DialogueController(
            scenario_key="A",
            patient=_make_patient(),
            display_message=messages.append,
            request_input=callbacks.append,
        )

        controller.start()
        callbacks.pop()("ja")
        callbacks.pop()("seit 2 Tagen")
        callbacks.pop()("ja")

        assert controller.state == DialogueState.END
        assert controller.summary is not None
        assert controller.summary.escalation_required is True
        assert "Bitte sofort dem Praxisteam melden" in " ".join(messages)


class TestAbortByPatient:
    """Fall 3: Patient bricht waehrend der Anamnese ab."""

    def test_patient_aborts_with_abbrechen(self) -> None:
        messages: list[str] = []
        callbacks: list = []

        controller = DialogueController(
            scenario_key="A",
            patient=_make_patient(),
            display_message=lambda text: messages.append(text),
            request_input=lambda cb: callbacks.append(cb),
        )

        controller.start()
        callbacks.pop()("ja")  # consent

        # Erste Frage beantworten
        assert controller.state == DialogueState.ANAMNESIS
        callbacks.pop()("3 Tage")

        # Bei zweiter Frage abbrechen
        callbacks.pop()("abbrechen")

        assert controller.state == DialogueState.END
        all_text = " ".join(messages)
        assert "abgebrochen" in all_text.lower()


class TestConsentDeclined:
    """Consent abgelehnt -> direktes Ende ohne Anamnese."""

    def test_decline_ends_dialogue(self) -> None:
        messages: list[str] = []
        callbacks: list = []

        controller = DialogueController(
            scenario_key="D",
            patient=_make_patient(),
            display_message=lambda text: messages.append(text),
            request_input=lambda cb: callbacks.append(cb),
        )

        controller.start()
        callbacks.pop()("nein")

        assert controller.state == DialogueState.END
        all_text = " ".join(messages)
        assert "abgelehnt" in all_text.lower() or "Praxispersonal" in all_text
