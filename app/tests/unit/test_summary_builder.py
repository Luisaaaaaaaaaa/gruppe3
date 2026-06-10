"""Unit-Tests fuer den Summary-Builder und strukturierte Zusammenfassung."""

from app.medical_rules.red_flag_engine import RedFlag
from app.output.summary_builder import AnamnesisSummary, build_grouped_sections, build_summary
from app.patient_import.patient_schema import PatientRecord


def _make_patient() -> PatientRecord:
    return PatientRecord(
        patient_id="P-TEST-001",
        first_name="Test",
        last_name="Patient",
        date_of_birth="1975-06-15",
    )


class TestBuildSummary:
    def test_basic_summary_fields(self) -> None:
        patient = _make_patient()
        summary = build_summary(
            patient=patient,
            scenario="A",
            answers={"symptom_dauer": "3 Tage"},
            vitals={"systolisch": 125, "diastolisch": 80},
            vitals_source="simuliert",
            red_flags=[],
        )
        assert summary.patient_id == "P-TEST-001"
        assert summary.patient_name == "Test Patient"
        assert summary.scenario == "A"
        assert summary.vitals_source == "simuliert"
        assert summary.synthetic is True

    def test_escalation_required_when_critical_flag(self) -> None:
        patient = _make_patient()
        flags = [
            RedFlag(rule_id="X", description="test", severity="critical", triggered_by="y")
        ]
        summary = build_summary(
            patient=patient,
            scenario="B",
            answers={},
            vitals=None,
            vitals_source="simuliert",
            red_flags=flags,
        )
        assert summary.escalation_required is True

    def test_no_escalation_for_warning_only(self) -> None:
        patient = _make_patient()
        flags = [
            RedFlag(rule_id="X", description="test", severity="warning", triggered_by="y")
        ]
        summary = build_summary(
            patient=patient,
            scenario="B",
            answers={},
            vitals=None,
            vitals_source="simuliert",
            red_flags=flags,
        )
        assert summary.escalation_required is False

    def test_open_points_for_empty_answers(self) -> None:
        patient = _make_patient()
        summary = build_summary(
            patient=patient,
            scenario="A",
            answers={"feld1": "", "feld2": "unbekannt", "feld3": "vorhanden"},
            vitals=None,
            vitals_source="simuliert",
            red_flags=[],
        )
        assert len(summary.open_points) == 2
        assert any("feld1" in p for p in summary.open_points)
        assert any("feld2" in p for p in summary.open_points)

    def test_no_open_points_when_all_filled(self) -> None:
        patient = _make_patient()
        summary = build_summary(
            patient=patient,
            scenario="A",
            answers={"feld1": "Antwort", "feld2": "Ja"},
            vitals=None,
            vitals_source="manuell",
            red_flags=[],
        )
        assert summary.open_points == []

    def test_vitals_none_becomes_empty_dict(self) -> None:
        patient = _make_patient()
        summary = build_summary(
            patient=patient,
            scenario="C",
            answers={},
            vitals=None,
            vitals_source="simuliert",
            red_flags=[],
        )
        assert summary.vitals == {}

    def test_timestamp_is_set(self) -> None:
        patient = _make_patient()
        summary = build_summary(
            patient=patient,
            scenario="A",
            answers={},
            vitals=None,
            vitals_source="simuliert",
            red_flags=[],
        )
        assert summary.timestamp != ""
        assert "T" in summary.timestamp

    def test_red_flags_preserved_in_summary(self) -> None:
        patient = _make_patient()
        flags = [
            RedFlag(rule_id="RF-1", description="A", severity="warning", triggered_by="x"),
            RedFlag(rule_id="RF-2", description="B", severity="critical", triggered_by="y"),
        ]
        summary = build_summary(
            patient=patient,
            scenario="B",
            answers={},
            vitals=None,
            vitals_source="simuliert",
            red_flags=flags,
        )
        assert len(summary.red_flags) == 2

    def test_no_diagnosis_output_in_red_flags(self) -> None:
        patient = _make_patient()
        summary = build_summary(
            patient=patient,
            scenario="D",
            answers={},
            vitals={"systolisch": 200},
            vitals_source="simuliert",
            red_flags=[
                RedFlag(rule_id="DM-RF-009", description="Hoher BD", severity="critical", triggered_by="sys=200")
            ],
        )
        for rf in summary.red_flags:
            desc = rf.description.lower()
            assert "diagnose" not in desc
            assert "therapie" not in desc
            assert "empfehlung" not in desc
            assert "entwarnung" not in desc


class TestBuildGroupedSections:
    def test_diabetes_scenario_has_sections(self) -> None:
        answers = {
            "gewicht_aktuell": "85",
            "gewichtsveraenderung": "nein",
            "blutdruck_systolisch": "130",
            "blutdruck_diastolisch": "85",
            "letzte_kontrolle": "vor 3 Monaten",
            "hypo_hyper_hinweise": "nein",
            "hypo_hyper_beschwerden": "",
            "bekannte_diagnosen": "Diabetes Typ 2",
            "folgeerkrankungen_bekannt": "nein",
            "folgeerkrankungen_details": "",
            "offene_wunde_fussproblem": "nein",
            "offene_wunde_fussproblem_details": "",
            "hba1c_bekannt": "ja",
            "hba1c_wert": "7,2",
            "blutzuckerwert_bekannt": "nein",
            "blutzuckerwert_details": "",
            "offene_fragen": "keine",
            "lebensstil": "regelmaessig Sport",
            "med_adhaerenz_0": "ja",
            "med_adhaerenz_1": "nein",
            "med_adhaerenz_grund_1": "Ich habe Nebenwirkungen",
        }
        sections = build_grouped_sections("D", answers, {})
        assert "Anamnese" in sections
        assert "Verlauf" in sections
        assert "Aktuelle Symptome" in sections
        assert "Medikation" in sections
        assert "Komplikationen" in sections
        assert "Vorbefunde" in sections
        assert "Offene Fragen" in sections

    def test_non_diabetes_no_diabetes_sections(self) -> None:
        sections = build_grouped_sections("A", {}, {})
        # Keine Antworten -> keine "Anamnese"-Sektion
        # Kein Diabetes -> keine Diabetes-Sektionen
        assert "Anamnese" not in sections
        assert "Verlauf" not in sections

    def test_gewichtsveraenderung_details_when_ja(self) -> None:
        answers = {
            "gewichtsveraenderung": "ja",
            "gewichtsveraenderung_details": "3 kg zugenommen",
        }
        sections = build_grouped_sections("diabetes", answers, {})
        assert sections["Verlauf"]["Gewichtsveraenderung"] == "3 kg zugenommen"

    def test_gewichtsveraenderung_none_when_nein(self) -> None:
        answers = {
            "gewichtsveraenderung": "nein",
            "gewichtsveraenderung_details": "irgendwas",
        }
        sections = build_grouped_sections("diabetes", answers, {})
        assert sections["Verlauf"]["Gewichtsveraenderung"] == "keine angegeben"

    def test_vitals_used_for_blutdruck(self) -> None:
        answers: dict[str, str] = {
            "blutdruck_systolisch": "",
            "blutdruck_diastolisch": "",
        }
        vitals = {"systolisch": 140, "diastolisch": 90}
        sections = build_grouped_sections("D", answers, vitals)
        assert "140" in sections["Verlauf"]["Blutdruck"]
        assert "90" in sections["Verlauf"]["Blutdruck"]
