from app.scenarios.diabetes_scenario import QUESTIONS, should_ask_follow_up


def test_patient_questions_avoid_key_diabetes_jargon() -> None:
    question_text = " ".join(question.text.lower() for question in QUESTIONS)
    assert "hypoglykämie" not in question_text
    assert "hyperglykämie" not in question_text
    assert "neuropathie" not in question_text
    assert "nephropathie" not in question_text


def test_follow_ups_only_appear_after_yes() -> None:
    assert should_ask_follow_up("hypo_hyper_beschwerden", {"hypo_hyper_hinweise": "ja"})
    assert not should_ask_follow_up("hypo_hyper_beschwerden", {"hypo_hyper_hinweise": "nein"})
    assert should_ask_follow_up("blutdruck_zu_hause_details", {"blutdruck_zu_hause": "ja"})
    assert not should_ask_follow_up("blutdruck_zu_hause_details", {"blutdruck_zu_hause": "nein"})
    assert should_ask_follow_up("alkohol", {"alkohol_konsum": "ja"})
    assert not should_ask_follow_up("alkohol", {"alkohol_konsum": "nein"})


def test_measurements_are_offered_when_values_are_unknown() -> None:
    answers = {
        "gewicht_aktuell": "unbekannt",
        "blutdruck_systolisch": "unbekannt",
        "blutdruck_diastolisch": "unbekannt",
    }
    assert should_ask_follow_up("gewicht_messen", answers)
    assert should_ask_follow_up("blutdruck_messen", answers)


def test_measurements_are_skipped_when_values_are_known() -> None:
    answers = {
        "gewicht_aktuell": "80",
        "blutdruck_systolisch": "130",
        "blutdruck_diastolisch": "80",
    }
    assert not should_ask_follow_up("gewicht_messen", answers)
    assert not should_ask_follow_up("blutdruck_messen", answers)
