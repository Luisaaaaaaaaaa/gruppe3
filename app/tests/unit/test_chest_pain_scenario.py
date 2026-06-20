from app.scenarios.chest_pain_scenario import QUESTIONS, berechne_marburger_herzscore


def test_questionnaire_contains_project_requirements() -> None:
    keys = {question.key for question in QUESTIONS}
    assert {
        "lokalisation",
        "beginn",
        "dauer",
        "schmerzcharakter",
        "ausstrahlung",
        "belastungsabhaengigkeit",
        "atemnot",
        "kaltschweissigkeit",
        "synkope",
        "ausgepraege_schwaeche",
        "kardiovaskulaere_risikofaktoren",
        "vorerkrankungen",
    } <= keys


def test_questionnaire_uses_supported_input_types() -> None:
    assert all(question.input_type in {"freitext", "ja_nein", "zahl"} for question in QUESTIONS)


def test_marburger_score_uses_all_five_original_criteria_for_man() -> None:
    result = berechne_marburger_herzscore(
        {
            "bekannte_khk": "ja",
            "belastungsabhaengigkeit": "ja",
            "druckschmerz_thoraxwand": "nein",
            "patient_vermutet_herz": "ja",
        },
        alter=55,
        geschlecht="männlich",
    )
    assert result["score"] == 5


def test_marburger_age_threshold_for_women_is_65() -> None:
    below_threshold = berechne_marburger_herzscore({}, alter=64, geschlecht="weiblich")
    at_threshold = berechne_marburger_herzscore({}, alter=65, geschlecht="weiblich")
    assert below_threshold["score"] == 0
    assert at_threshold["score"] == 1


def test_radiation_is_not_used_as_patient_suspicion_proxy() -> None:
    result = berechne_marburger_herzscore(
        {"ausstrahlung": "linker Arm", "patient_vermutet_herz": "nein"},
        alter=40,
        geschlecht="männlich",
    )
    assert result["score"] == 0


def test_unknown_pressure_reproducibility_does_not_score() -> None:
    result = berechne_marburger_herzscore({"druckschmerz_thoraxwand": ""})
    assert result["score"] == 0
