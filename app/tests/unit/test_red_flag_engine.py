"""Unit-Tests fuer die Red-Flag-Engine (alle Szenarien).

Testet regelbasierte Erkennung von Warnzeichen je Szenario,
Eskalationsstufen (warning vs. critical) und korrekte Ausloesung.
"""

import pytest

from app.medical_rules.red_flag_engine import (
    RedFlag,
    check,
    check_chest_pain,
    check_cough,
    check_diabetes,
    check_hypertension,
)


# ========================================================================
# Husten / Atemwegsinfekt (Szenario A)
# ========================================================================


class TestCheckCough:
    def test_no_flags_for_routine_case(self) -> None:
        answers = {
            "dyspnoe": "nein",
            "belastungsdyspnoe": "nein",
            "blutbeimengung": "nein",
            "fieber": "nein",
            "thorakale_schmerzen": "nein",
            "vorerkrankungen": "keine",
            "auswurf_farbe": "klar",
        }
        flags = check_cough(answers)
        assert flags == []

    def test_dyspnoea_requires_review(self) -> None:
        answers = {"dyspnoe": "ja"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-001" and f.severity == "warning" for f in flags)

    def test_haemoptysen_critical(self) -> None:
        answers = {"blutbeimengung": "ja"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-002" and f.severity == "critical" for f in flags)

    def test_high_fever_warning(self) -> None:
        answers = {"fieber": "ja", "korpertemperatur": "39,4 °C"}
        flags = check_cough(answers)
        rf = next(f for f in flags if f.rule_id == "COUGH-RF-003")
        assert rf.severity == "warning"

    def test_very_high_fever_critical(self) -> None:
        answers = {"fieber": "ja", "korpertemperatur": "40,0 °C"}
        flags = check_cough(answers)
        rf = next(f for f in flags if f.rule_id == "COUGH-RF-003")
        assert rf.severity == "critical"

    def test_fever_plus_dyspnoea_critical(self) -> None:
        answers = {"fieber": "ja", "dyspnoe": "ja"}
        flags = check_cough(answers)
        rf = next(f for f in flags if f.rule_id == "COUGH-RF-010")
        assert rf.severity == "critical"

    def test_fever_plus_chest_pain_critical(self) -> None:
        answers = {"fieber": "ja", "thorakale_schmerzen": "ja"}
        flags = check_cough(answers)
        rf = next(f for f in flags if f.rule_id == "COUGH-RF-010")
        assert rf.severity == "critical"

    def test_thorakale_schmerzen_warning(self) -> None:
        answers = {"thorakale_schmerzen": "ja"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-004" and f.severity == "warning" for f in flags)

    def test_relevante_vorerkrankung_copd_warning(self) -> None:
        answers = {"vorerkrankungen": "COPD seit 5 Jahren", "fieber": "nein"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-005" and f.severity == "warning" for f in flags)

    def test_relevante_vorerkrankung_plus_fieber_critical(self) -> None:
        answers = {"vorerkrankungen": "Asthma bronchiale", "fieber": "ja"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-005" and f.severity == "critical" for f in flags)

    def test_immunsuppression_detected(self) -> None:
        answers = {"vorerkrankungen": "Immunsuppression nach Transplantation", "fieber": "nein"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-005" and f.severity == "critical" for f in flags)

    def test_herzinsuffizienz_detected(self) -> None:
        answers = {"vorerkrankungen": "Herzinsuffizienz NYHA III", "fieber": "nein"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-005" for f in flags)

    def test_irrelevante_vorerkrankung_no_flag(self) -> None:
        answers = {"vorerkrankungen": "Heuschnupfen", "fieber": "nein"}
        flags = check_cough(answers)
        assert not any(f.rule_id == "COUGH-RF-005" for f in flags)

    def test_belastungsdyspnoe_without_ruhedyspnoe_warning(self) -> None:
        answers = {"belastungsdyspnoe": "ja", "dyspnoe": "nein"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-006" and f.severity == "warning" for f in flags)

    def test_belastungsdyspnoe_with_ruhedyspnoe_no_separate_flag(self) -> None:
        answers = {"belastungsdyspnoe": "ja", "dyspnoe": "ja"}
        flags = check_cough(answers)
        assert not any(f.rule_id == "COUGH-RF-006" for f in flags)

    def test_spo2_below_92_critical(self) -> None:
        flags = check_cough({}, vitals={"spo2": 88})
        assert any(f.rule_id == "COUGH-RF-007" and f.severity == "critical" for f in flags)

    def test_spo2_92_to_94_warning(self) -> None:
        flags = check_cough({}, vitals={"spo2": 93})
        assert any(f.rule_id == "COUGH-RF-008" and f.severity == "warning" for f in flags)

    def test_spo2_normal_no_flag(self) -> None:
        flags = check_cough({}, vitals={"spo2": 97})
        assert not any(f.rule_id in ("COUGH-RF-007", "COUGH-RF-008") for f in flags)

    def test_blutiger_auswurf_freitext_critical(self) -> None:
        answers = {"auswurf_farbe": "blutig, rostfarben", "blutbeimengung": "nein"}
        flags = check_cough(answers)
        assert any(f.rule_id == "COUGH-RF-009" and f.severity == "critical" for f in flags)

    def test_blutiger_auswurf_no_duplicate_with_blutbeimengung(self) -> None:
        answers = {"auswurf_farbe": "blutig", "blutbeimengung": "ja"}
        flags = check_cough(answers)
        assert not any(f.rule_id == "COUGH-RF-009" for f in flags)

    def test_missing_fields_no_crash(self) -> None:
        flags = check_cough({})
        assert flags == []

    @pytest.mark.parametrize(
        ("key", "rule_id"),
        [
            ("ruhedyspnoe", "COUGH-RF-011"),
            ("sprechen_beeintraechtigt", "COUGH-RF-012"),
            ("zyanose", "COUGH-RF-013"),
            ("verwirrtheit", "COUGH-RF-014"),
            ("ohnmacht", "COUGH-RF-015"),
            ("auffaelliges_atemgeraeusch", "COUGH-RF-016"),
            ("rauch_reizstoffe", "COUGH-RF-017"),
            ("rasche_verschlechterung", "COUGH-RF-018"),
        ],
    )
    def test_direct_warning_signs_are_critical(self, key: str, rule_id: str) -> None:
        flags = check_cough({key: "ja"})
        assert any(f.rule_id == rule_id and f.severity == "critical" for f in flags)

    def test_respiratory_rate_30_is_critical(self) -> None:
        flags = check_cough({"atemfrequenz": "30 Atemzüge"})
        assert any(f.rule_id == "COUGH-RF-021" and f.severity == "critical" for f in flags)

    def test_very_poor_general_condition_is_critical(self) -> None:
        flags = check_cough({"reduzierter_allgemeinzustand": "ja"})
        assert any(f.rule_id == "COUGH-RF-019" and f.severity == "critical" for f in flags)

    def test_pulse_120_is_critical(self) -> None:
        flags = check_cough({}, vitals={"puls": 120})
        assert any(f.rule_id == "COUGH-RF-022" and f.severity == "critical" for f in flags)

    def test_multiple_flags_severe_case(self) -> None:
        answers = {
            "dyspnoe": "ja",
            "blutbeimengung": "ja",
            "fieber": "ja",
            "thorakale_schmerzen": "ja",
            "vorerkrankungen": "COPD",
        }
        flags = check_cough(answers)
        assert len(flags) >= 4


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

    def test_headache_warning_normal_bp(self) -> None:
        answers = {"kopfschmerz": "ja", "blutdruck_systolisch": "150"}
        flags = check_hypertension(answers)
        rf = next(f for f in flags if f.rule_id == "HYP-RF-007")
        assert rf.severity == "warning"

    def test_headache_critical_with_high_bp(self) -> None:
        answers = {"kopfschmerz": "ja", "blutdruck_systolisch": "195"}
        flags = check_hypertension(answers)
        rf = next(f for f in flags if f.rule_id == "HYP-RF-007")
        assert rf.severity == "critical"

    def test_multiple_organ_symptoms_plus_high_bp(self) -> None:
        answers = {
            "kopfschmerz": "ja",
            "atemnot": "ja",
            "blutdruck_systolisch": "170",
        }
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-008" and f.severity == "critical" for f in flags)

    def test_multiple_organ_symptoms_low_bp_no_rf008(self) -> None:
        answers = {
            "kopfschmerz": "ja",
            "atemnot": "ja",
            "blutdruck_systolisch": "140",
        }
        flags = check_hypertension(answers)
        assert not any(f.rule_id == "HYP-RF-008" for f in flags)

    def test_grade2_systolic_160_warning(self) -> None:
        answers = {"blutdruck_systolisch": "165"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-009" and f.severity == "warning" for f in flags)

    def test_grade2_diastolic_100_warning(self) -> None:
        answers = {"blutdruck_diastolisch": "105"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-010" and f.severity == "warning" for f in flags)

    def test_relevant_preexisting_condition_warning(self) -> None:
        answers = {"vorerkrankungen": "Herzinfarkt vor 2 Jahren", "blutdruck_systolisch": "145"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-011" and f.severity == "warning" for f in flags)

    def test_relevant_preexisting_condition_critical_with_high_bp(self) -> None:
        answers = {"vorerkrankungen": "KHK seit langem", "blutdruck_systolisch": "175"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-011" and f.severity == "critical" for f in flags)

    def test_irrelevant_preexisting_no_rf011(self) -> None:
        answers = {"vorerkrankungen": "Heuschnupfen", "blutdruck_systolisch": "180"}
        flags = check_hypertension(answers)
        assert not any(f.rule_id == "HYP-RF-011" for f in flags)

    def test_tachycardia_critical(self) -> None:
        answers = {"puls": "125"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-012" and f.severity == "critical" for f in flags)

    def test_bradycardia_warning(self) -> None:
        answers = {"puls": "45"}
        flags = check_hypertension(answers)
        assert any(f.rule_id == "HYP-RF-013" and f.severity == "warning" for f in flags)

    def test_normal_pulse_no_flag(self) -> None:
        answers = {"puls": "72"}
        flags = check_hypertension(answers)
        assert not any(f.rule_id in ("HYP-RF-012", "HYP-RF-013") for f in flags)

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

    def test_severe_weakness_critical(self) -> None:
        answers = {"ausgepraege_schwaeche": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-007" and f.severity == "critical" for f in flags)

    @pytest.mark.parametrize(
        ("key", "rule_id"),
        [
            ("ruhedyspnoe", "CP-RF-015"),
            ("verwirrtheit", "CP-RF-016"),
            ("rasche_verschlechterung", "CP-RF-017"),
        ],
    )
    def test_new_direct_warning_signs_are_critical(self, key: str, rule_id: str) -> None:
        flags = check_chest_pain({key: "ja"})
        assert any(f.rule_id == rule_id and f.severity == "critical" for f in flags)

    def test_current_severe_pain_is_critical(self) -> None:
        flags = check_chest_pain({"schmerzen_aktuell": "ja", "schmerzstaerke": "8"})
        assert any(f.rule_id == "CP-RF-018" and f.severity == "critical" for f in flags)

    def test_persistent_current_pain_is_critical(self) -> None:
        flags = check_chest_pain({"schmerzen_aktuell": "ja", "dauer": "seit 30 Minuten"})
        assert any(f.rule_id == "CP-RF-019" and f.severity == "critical" for f in flags)

    def test_nausea_plus_cold_sweat_critical(self) -> None:
        answers = {"uebelkeit": "ja", "kaltschweissigkeit": "ja"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-008" and f.severity == "critical" for f in flags)

    def test_nausea_alone_no_cp_rf_008(self) -> None:
        answers = {"uebelkeit": "ja", "kaltschweissigkeit": "nein"}
        flags = check_chest_pain(answers)
        assert not any(f.rule_id == "CP-RF-008" for f in flags)

    def test_pressing_pain_no_rest_improvement_critical(self) -> None:
        answers = {"schmerzcharakter": "drückend", "ruhe_besserung": "nein"}
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-009" and f.severity == "critical" for f in flags)

    def test_pressing_pain_rest_improvement_no_rf009(self) -> None:
        answers = {"schmerzcharakter": "drückend", "ruhe_besserung": "ja"}
        flags = check_chest_pain(answers)
        assert not any(f.rule_id == "CP-RF-009" for f in flags)

    def test_age_plus_risk_factors_warning(self) -> None:
        answers = {
            "alter_ueber_55": "ja",
            "kardiovaskulaere_risikofaktoren": "Rauchen, Diabetes",
        }
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-010" and f.severity == "warning" for f in flags)

    def test_age_without_risk_factors_no_rf010(self) -> None:
        answers = {
            "alter_ueber_55": "ja",
            "kardiovaskulaere_risikofaktoren": "keine",
        }
        flags = check_chest_pain(answers)
        assert not any(f.rule_id == "CP-RF-010" for f in flags)

    def test_no_palpation_pain_plus_exertion_warning(self) -> None:
        answers = {
            "druckschmerz_thoraxwand": "nein",
            "belastungsabhaengigkeit": "ja",
        }
        flags = check_chest_pain(answers)
        assert any(f.rule_id == "CP-RF-011" and f.severity == "warning" for f in flags)

    def test_palpation_pain_yes_no_rf011(self) -> None:
        answers = {
            "druckschmerz_thoraxwand": "ja",
            "belastungsabhaengigkeit": "ja",
        }
        flags = check_chest_pain(answers)
        assert not any(f.rule_id == "CP-RF-011" for f in flags)

    def test_high_bp_systolic_critical(self) -> None:
        flags = check_chest_pain({}, vitals={"systolisch": 190})
        assert any(f.rule_id == "CP-RF-012" and f.severity == "critical" for f in flags)

    def test_high_bp_diastolic_critical(self) -> None:
        flags = check_chest_pain({}, vitals={"diastolisch": 125})
        assert any(f.rule_id == "CP-RF-013" and f.severity == "critical" for f in flags)

    def test_low_spo2_critical(self) -> None:
        flags = check_chest_pain({}, vitals={"spo2": 88})
        assert any(f.rule_id == "CP-RF-014" and f.severity == "critical" for f in flags)

    def test_normal_vitals_no_vital_flags(self) -> None:
        flags = check_chest_pain({}, vitals={"systolisch": 130, "diastolisch": 80, "spo2": 97})
        assert not any(f.rule_id in ("CP-RF-012", "CP-RF-013", "CP-RF-014") for f in flags)

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

    def test_hba1c_very_high_critical(self) -> None:
        answers = {"hba1c_wert": "11,2"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-011" and f.severity == "critical" for f in flags)

    def test_hba1c_high_warning(self) -> None:
        answers = {"hba1c_wert": "9,0"}
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-012" and f.severity == "warning" for f in flags)

    def test_hba1c_acceptable_no_flag(self) -> None:
        answers = {"hba1c_wert": "7,2"}
        flags = check_diabetes(answers)
        assert not any(f.rule_id in ("DM-RF-011", "DM-RF-012") for f in flags)

    def test_significant_weight_loss_warning(self) -> None:
        answers = {
            "gewichtsveraenderung": "ja",
            "gewichtsveraenderung_details": "6 kg abgenommen in 4 Wochen",
        }
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-013" and f.severity == "warning" for f in flags)

    def test_small_weight_loss_no_flag(self) -> None:
        answers = {
            "gewichtsveraenderung": "ja",
            "gewichtsveraenderung_details": "2 kg abgenommen",
        }
        flags = check_diabetes(answers)
        assert not any(f.rule_id == "DM-RF-013" for f in flags)

    def test_weight_gain_no_flag(self) -> None:
        answers = {
            "gewichtsveraenderung": "ja",
            "gewichtsveraenderung_details": "3 kg zugenommen",
        }
        flags = check_diabetes(answers)
        assert not any(f.rule_id == "DM-RF-013" for f in flags)

    def test_complications_plus_hypo_signs_critical(self) -> None:
        answers = {
            "folgeerkrankungen_bekannt": "ja",
            "folgeerkrankungen_details": "Neuropathie",
            "hypo_hyper_hinweise": "ja",
        }
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-014" and f.severity == "critical" for f in flags)

    def test_complications_without_symptoms_no_rf014(self) -> None:
        answers = {
            "folgeerkrankungen_bekannt": "ja",
            "folgeerkrankungen_details": "Neuropathie",
            "hypo_hyper_hinweise": "nein",
        }
        flags = check_diabetes(answers)
        assert not any(f.rule_id == "DM-RF-014" for f in flags)

    def test_nephropathy_warning(self) -> None:
        answers = {
            "folgeerkrankungen_bekannt": "ja",
            "folgeerkrankungen_details": "diabetische Nephropathie Stadium 3",
        }
        flags = check_diabetes(answers)
        assert any(f.rule_id == "DM-RF-015" and f.severity == "warning" for f in flags)

    def test_insulin_plus_hypo_symptoms_critical(self) -> None:
        answers = {
            "hypo_hyper_hinweise": "ja",
            "hypo_hyper_beschwerden": "Zittern und Schweissausbruch",
        }
        flags = check_diabetes(answers, patient_medications=["Insulin Lantus"])
        assert any(f.rule_id == "DM-RF-016" and f.severity == "critical" for f in flags)

    def test_sulfonylharnstoff_plus_hypo_critical(self) -> None:
        answers = {
            "hypo_hyper_hinweise": "ja",
            "hypo_hyper_beschwerden": "starker Schwindel und Schwaeche",
        }
        flags = check_diabetes(answers, patient_medications=["Glimepirid"])
        assert any(f.rule_id == "DM-RF-016" and f.severity == "critical" for f in flags)

    def test_metformin_hypo_no_rf016(self) -> None:
        answers = {
            "hypo_hyper_hinweise": "ja",
            "hypo_hyper_beschwerden": "Zittern",
        }
        flags = check_diabetes(answers, patient_medications=["Metformin"])
        assert not any(f.rule_id == "DM-RF-016" for f in flags)

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

    def test_routes_to_cough(self) -> None:
        answers = {"dyspnoe": "ja"}
        flags = check("cough", answers)
        assert any(f.rule_id.startswith("COUGH") for f in flags)


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
