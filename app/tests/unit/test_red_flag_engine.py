"""Unit-Tests fuer die Red-Flag-Engine (alle Szenarien).

Testet regelbasierte Erkennung von Warnzeichen je Szenario,
Eskalationsstufen (warning vs. critical) und korrekte Ausloesung.
"""

import pytest

from app.medical_rules.red_flag_engine import (
    RedFlag,
    check,
    check_chest_pain,
    check_diabetes,
    check_hypertension,
)


# ========================================================================
# Hypertonie (Szenario C)
# ========================================================================


class TestCheckHypertension:
    def test_no_flags_for_routine_case(self) -> None:
        answers = {
            "blutdruck_systolisch": "130",
            "blutdruck_diastolisch": "85",
            "brustschmerz": "nein",
            "atemnot": "nein",
            "neurologische_symptome": "nein",
            "sehstoerungen": "nein",
        }
        flags = check_hypertension(answers)
        assert flags == []

    def test_critical_systolic_180(self) -> None:
        answers = {"blutdruck_systolisch": "185"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-001" and f.severity == "critical" for f in flags)

    def test_critical_diastolic_120(self) -> None:
        answers = {"blutdruck_diastolisch": "125"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-002" and f.severity == "critical" for f in flags)

    def test_chest_pain_critical(self) -> None:
        answers = {"brustschmerz": "ja"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-003" and f.severity == "critical" for f in flags)

    def test_dyspnoe_warning(self) -> None:
        answers = {"atemnot": "ja"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-004" and f.severity == "warning" for f in flags)

    def test_neurological_symptoms_critical(self) -> None:
        answers = {"neurologische_symptome": "ja"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-005" and f.severity == "critical" for f in flags)

    def test_visual_disturbance_critical_with_high_bp(self) -> None:
        answers = {"sehstoerungen": "ja", "blutdruck_systolisch": "190"}
        flags = check_hypertension(answers)
        rf = next(f for f in flags if f.rule_id == "HYP-RF-006")
        assert rf.severity == "critical"

    def test_visual_disturbance_warning_with_normal_bp(self) -> None:
        answers = {"sehstoerungen": "ja", "blutdruck_systolisch": "130"}
        flags = check_hypertension(answers)
        rf = next(f for f in flags if f.rule_id == "HYP-RF-006")
        assert rf.severity == "warning"

    def test_vitals_override_answers(self) -> None:
        answers: dict[str, str] = {}
        vitals = {"systolisch": 200, "diastolisch": 130}
        flags = check_hypertension(answers, vitals)
        assert any(f.rule_id == "HYP-RF-001" for f in flags)
        assert any(f.rule_id == "HYP-RF-002" for f in flags)

    def test_comma_number_parsing(self) -> None:
        answers = {"blutdruck_systolisch": "185,5"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-001" for f in flags)

    def test_missing_fields_no_crash(self) -> None:
        flags = check_hypertension({})
        assert flags == []


# ========================================================================
# Brustschmerz (Szenario B)
# ========================================================================


class TestCheckChestPain:
    def test_no_flags_for_routine_case(self) -> None:
        answers = {
            "atemnot": "nein",
            "kaltschweissigkeit": "nein",
            "synkope": "nein",
            "ausstrahlung": "keine",
            "schmerzcharakter": "stechend",
            "belastungsabhaengigkeit": "nein",
            "bekannte_khk": "nein",
            "ausgepraege_schwaeche": "nein",
            "uebelkeit": "nein",
        }
        flags = check_chest_pain(answers)
        assert flags == []

    def test_dyspnoe_critical(self) -> None:
        answers = {"atemnot": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-001" and f.severity == "critical" for f in flags)

    def test_cold_sweat_critical(self) -> None:
        answers = {"kaltschweissigkeit": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-002" and f.severity == "critical" for f in flags)

    def test_syncope_critical(self) -> None:
        answers = {"synkope": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-003" and f.severity == "critical" for f in flags)

    def test_radiation_left_arm(self) -> None:
        answers = {"ausstrahlung": "linker Arm"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-004" and f.severity == "critical" for f in flags)

    def test_radiation_jaw(self) -> None:
        answers = {"ausstrahlung": "Kiefer und Hals"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-004" for f in flags)

    def test_radiation_both_arms(self) -> None:
        answers = {"ausstrahlung": "beide Arme"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-004" for f in flags)

    def test_pressing_pain_with_exertion(self) -> None:
        answers = {"schmerzcharakter": "drückend", "belastungsabhaengigkeit": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-005" and f.severity == "critical" for f in flags)

    def test_pressing_pain_without_exertion_no_flag(self) -> None:
        answers = {"schmerzcharakter": "drückend", "belastungsabhaengigkeit": "nein"}
        flags = check_chest_pain(answers)
        assert not any(f.rule_id == "CP-RF-005" for f in flags)

    def test_known_chd_warning(self) -> None:
        answers = {"bekannte_khk": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-006" and f.severity == "warning" for f in flags)

    def test_severe_weakness_warning(self) -> None:
        answers = {"ausgepraege_schwaeche": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-007" and f.severity == "warning" for f in flags)

    def test_nausea_plus_cold_sweat_critical(self) -> None:
        answers = {"uebelkeit": "ja", "kaltschweissigkeit": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-008" and f.severity == "critical" for f in flags)

    def test_nausea_alone_no_cp_rf_008(self) -> None:
        answers = {"uebelkeit": "ja", "kaltschweissigkeit": "nein"}
        flags = check_chest_pain(answers)
        assert not any(f.rule_id == "CP-RF-008" for f in flags)

    def test_missing_fields_no_crash(self) -> None:
        flags = check_chest_pain({})
        assert flags == []

    def test_multiple_flags_at_once(self) -> None:
        answers = {
            "atemnot": "ja",
            "kaltschweissigkeit": "ja",
            "synkope": "ja",
            "ausstrahlung": "linker Arm",
        }
        flags = check_chest_pain(answers)
        assert len(flags) >= 4


# ========================================================================
# Diabetes (Szenario D)
# ========================================================================


class TestCheckDiabetes:
    def test_no_flags_for_routine_case(self) -> None:
        answers = {
            "hypo_hyper_hinweise": "nein",
            "hypo_hyper_beschwerden": "keine",
            "offene_wunde_fussproblem": "nein",
            "blutzuckerwert_details": "110",
            "blutdruck_systolisch": "130",
            "blutdruck_diastolisch": "80",
        }
        flags = check_diabetes(answers)
        assert flags == []

    def test_hypo_hyper_warning(self) -> None:
        answers = {"hypo_hyper_hinweise": "ja"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-001" and f.severity == "warning" for f in flags)

    def test_confusion_critical(self) -> None:
        answers = {"hypo_hyper_beschwerden": "Patient ist verwirrt"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-002" and f.severity == "critical" for f in flags)

    def test_unconsciousness_critical(self) -> None:
        answers = {"hypo_hyper_beschwerden": "Bewusstlosigkeit"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-002" and f.severity == "critical" for f in flags)

    def test_vomiting_critical(self) -> None:
        answers = {"hypo_hyper_beschwerden": "starkes Erbrechen seit heute morgen"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-003" and f.severity == "critical" for f in flags)

    def test_dyspnoe_in_diabetes_critical(self) -> None:
        answers = {"hypo_hyper_beschwerden": "Atemnot und Schwindel"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-003" and f.severity == "critical" for f in flags)

    def test_chest_pain_in_diabetes_critical(self) -> None:
        answers = {"hypo_hyper_beschwerden": "Brustschmerz seit einer Stunde"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-004" and f.severity == "critical" for f in flags)

    def test_visual_disturbance_warning(self) -> None:
        answers = {"hypo_hyper_beschwerden": "Sehstoerungen seit gestern"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-005" and f.severity == "warning" for f in flags)

    def test_foot_wound_warning(self) -> None:
        answers = {
            "offene_wunde_fussproblem": "ja",
            "offene_wunde_fussproblem_details": "kleine Blase am Zeh",
        }
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-006" and f.severity == "warning" for f in flags)

    def test_foot_wound_critical_when_worsening(self) -> None:
        answers = {
            "offene_wunde_fussproblem": "ja",
            "offene_wunde_fussproblem_details": "Wunde verschlechtert sich stark",
        }
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-006" and f.severity == "critical" for f in flags)

    def test_foot_wound_critical_with_infection(self) -> None:
        answers = {
            "offene_wunde_fussproblem": "ja",
            "offene_wunde_fussproblem_details": "entzuendete Stelle am Fuss",
        }
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-006" and f.severity == "critical" for f in flags)

    def test_low_blood_sugar_critical(self) -> None:
        answers = {"blutzuckerwert_details": "55 mg/dl"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-007" and f.severity == "critical" for f in flags)

    def test_high_blood_sugar_critical(self) -> None:
        answers = {"blutzuckerwert_details": "350 mg/dl"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-008" and f.severity == "critical" for f in flags)

    def test_normal_blood_sugar_no_flag(self) -> None:
        answers = {"blutzuckerwert_details": "110 mg/dl"}
        flags = check_diabetes(answers)
        assert not any(f.rule_id in ("DM-RF-007", "DM-RF-008") for f in flags)

    def test_critical_systolic_bp(self) -> None:
        answers = {"blutdruck_systolisch": "190"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-009" and f.severity == "critical" for f in flags)

    def test_critical_diastolic_bp(self) -> None:
        answers = {"blutdruck_diastolisch": "125"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-010" and f.severity == "critical" for f in flags)

    def test_vitals_used_for_bp(self) -> None:
        answers: dict[str, str] = {}
        vitals = {"systolisch": 185, "diastolisch": 125}
        flags = check_diabetes(answers, vitals)
        assert any(f.rule_id == "DM-RF-009" for f in flags)
        assert any(f.rule_id == "DM-RF-010" for f in flags)

    def test_missing_fields_no_crash(self) -> None:
        flags = check_diabetes({})
        assert flags == []


# ========================================================================
# Dispatcher check()
# ========================================================================


class TestCheckDispatcher:
    def test_routes_to_hypertension(self) -> None:
        answers = {"blutdruck_systolisch": "200"}
        flags = check("hypertension", answers)
        assert any(f.rule_id.startswith("HYP") for f in flags)

    def test_routes_to_chest_pain(self) -> None:
        answers = {"synkope": "ja"}
        flags = check("chest_pain", answers)
        assert any(f.rule_id.startswith("CP") for f in flags)

    def test_routes_to_diabetes(self) -> None:
        answers = {"hypo_hyper_hinweise": "ja"}
        flags = check("diabetes", answers)
        assert any(f.rule_id.startswith("DM") for f in flags)

    def test_unknown_scenario_returns_empty(self) -> None:
        flags = check("unknown", {"atemnot": "ja"})
        assert flags == []

    def test_cough_returns_empty_currently(self) -> None:
        flags = check("cough", {"atemnot": "ja"})
        assert flags == []


# ========================================================================
# RedFlag dataclass
# ========================================================================


class TestRedFlagDataclass:
    def test_is_frozen(self) -> None:
        rf = RedFlag(rule_id="X", description="Y", severity="warning", triggered_by="Z")
        with pytest.raises(Exception):
            rf.rule_id = "changed"

    def test_fields_accessible(self) -> None:
        rf = RedFlag(rule_id="A", description="B", severity="critical", triggered_by="C")
        assert rf.rule_id == "A"
        assert rf.description == "B"
        assert rf.severity == "critical"
        assert rf.triggered_by == "C"
