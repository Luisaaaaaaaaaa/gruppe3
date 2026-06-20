from app.scenarios.hypertension_scenario import AnamnesisQuestion


SCENARIO_KEY = "diabetes"
SCENARIO_TITLE = "Szenario D: Typ-2-Diabetes / metabolische Verlaufskontrolle"

# Grundlage: NVL Typ-2-Diabetes, Kurzfassung Version 3.0 (2023), Kapitel 4,
# sowie die Vorgaben des Semesterprojekts zu Szenario D. Der Fragebogen ist
# für eine Verlaufskontrolle gedacht. Untersuchungen und Laborwerte werden
# lediglich vorbereitet bzw. dokumentiert; eine Diagnose oder Empfehlung
# erfolgt nicht.
QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion(
        "bekannte_diagnosen",
        "Welche Krankheiten sind bei Ihnen bekannt? Denken Sie bitte auch an hohen Blutdruck sowie Probleme mit Herz, Nieren oder Augen.",
    ),
    AnamnesisQuestion(
        "allgemeinbefinden",
        "Wie fühlen Sie sich heute? Was ist anders als bei Ihrer letzten Kontrolle?",
    ),
    AnamnesisQuestion("starker_durst", "Hatten Sie in letzter Zeit ungewöhnlich starken Durst?", input_type="ja_nein"),
    AnamnesisQuestion("haeufiges_wasserlassen", "Müssen Sie häufiger Wasser lassen als sonst?", input_type="ja_nein"),
    AnamnesisQuestion("muedigkeit_schwaeche", "Fühlen Sie sich ungewöhnlich müde, schwach oder benommen?", input_type="ja_nein"),
    AnamnesisQuestion(
        "hypo_hyper_hinweise",
        "Hatten Sie Zittern, starkes Schwitzen, Herzklopfen, großen Hunger oder Schwindel?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "hypo_hyper_beschwerden",
        "Welche Beschwerden hatten Sie genau? Wann traten sie auf und wie lange dauerten sie?",
        required=False,
    ),
    AnamnesisQuestion(
        "akutes_erbrechen_atmung",
        "Haben Sie gerade Übelkeit mit Erbrechen, starke Bauchschmerzen oder atmen Sie ungewöhnlich schnell oder tief?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "akut_verwirrt_bewusstlos",
        "Waren Sie heute verwirrt, kaum ansprechbar, ohnmächtig oder bewusstlos?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "brustschmerz",
        "Haben Sie gerade Schmerzen oder starken Druck in der Brust?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "atemnot",
        "Bekommen Sie gerade deutlich schlechter Luft als sonst?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "sehstoerungen",
        "Sehen Sie plötzlich verschwommen, doppelt oder deutlich schlechter als sonst?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "gewicht_aktuell",
        "Wie viel wiegen Sie aktuell in Kilogramm? Wählen Sie „unbekannt“, wenn Sie es nicht wissen.",
        input_type="zahl",
        slider_min=30,
        slider_max=300,
        slider_step=1,
    ),
    AnamnesisQuestion("gewicht_messen", "Bitte wiegen Sie sich jetzt.", required=False),
    AnamnesisQuestion("gewichtsveraenderung", "Hat sich Ihr Gewicht seit der letzten Kontrolle verändert?", input_type="ja_nein"),
    AnamnesisQuestion(
        "gewichtsveraenderung_details",
        "Haben Sie zu- oder abgenommen? Um wie viele Kilogramm und in welchem Zeitraum?",
        required=False,
    ),
    AnamnesisQuestion("blutdruck_zu_hause", "Haben Sie seit der letzten Kontrolle zu Hause Blutdruck gemessen?", input_type="ja_nein"),
    AnamnesisQuestion(
        "blutdruck_zu_hause_details",
        "Welche Werte hatten Sie ungefähr und wann wurden sie gemessen?",
        required=False,
    ),
    AnamnesisQuestion(
        "blutdruck_systolisch",
        "Wie hoch ist der obere Blutdruckwert? Wählen Sie „unbekannt“, wenn er nicht vorliegt.",
        input_type="zahl",
        slider_min=80,
        slider_max=250,
        slider_step=1,
    ),
    AnamnesisQuestion(
        "blutdruck_diastolisch",
        "Wie hoch ist der untere Blutdruckwert? Wählen Sie „unbekannt“, wenn er nicht vorliegt.",
        input_type="zahl",
        slider_min=40,
        slider_max=150,
        slider_step=1,
    ),
    AnamnesisQuestion("blutdruck_messen", "Bitte messen Sie jetzt Ihren Blutdruck.", required=False),
    AnamnesisQuestion(
        "folgeerkrankungen_bekannt",
        "Sind bei Ihnen durch den Diabetes Probleme an Augen, Nieren, Nerven, Füßen, Herz oder Kreislauf bekannt?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion("folgeerkrankungen_details", "Welche dieser Probleme sind bekannt?", required=False),
    AnamnesisQuestion(
        "offene_wunde_fussproblem",
        "Haben Sie offene Stellen, Blasen, Druckstellen, Rötungen oder andere Wunden an den Füßen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "offene_wunde_fussproblem_details",
        "Seit wann besteht die Stelle? Ist sie wärmer, geschwollen, nässt sie oder wird sie schlimmer?",
        required=False,
    ),
    AnamnesisQuestion(
        "gefuehlsstoerungen_fuesse",
        "Spüren Sie Kribbeln, Brennen, Schmerzen oder Taubheit in den Füßen oder Beinen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion("letzte_fusskontrolle", "Wann wurden Ihre Füße zuletzt untersucht?", required=False),
    AnamnesisQuestion("letzte_augenkontrolle", "Wann wurden Ihre Augen zuletzt ärztlich untersucht?", required=False),
    AnamnesisQuestion("letzte_nierenkontrolle", "Wann wurden zuletzt Blut und Urin zur Kontrolle Ihrer Nieren untersucht?", required=False),
    AnamnesisQuestion("hba1c_bekannt", "Kennen Sie Ihren letzten Langzeit-Blutzuckerwert? Er zeigt den durchschnittlichen Blutzucker der vergangenen Wochen.", input_type="ja_nein"),
    AnamnesisQuestion("hba1c_wert", "Wie hoch war dieser Langzeit-Blutzuckerwert und wann wurde er bestimmt?", required=False),
    AnamnesisQuestion("blutzuckerwert_bekannt", "Kennen Sie einen anderen zuletzt gemessenen Blutzuckerwert?", input_type="ja_nein"),
    AnamnesisQuestion(
        "blutzuckerwert_details",
        "Wie hoch war der Wert, wann wurde er gemessen und war das vor oder nach dem Essen?",
        required=False,
    ),
    AnamnesisQuestion("letzte_kontrolle", "Wann war Ihre letzte Diabetes-Kontrolle?"),
    AnamnesisQuestion("bewegung", "An wie vielen Tagen pro Woche bewegen Sie sich mindestens etwa 30 Minuten?", required=False),
    AnamnesisQuestion("ernaehrung", "Hat sich Ihre Ernährung seit der letzten Kontrolle verändert? Wenn ja, wie?", required=False),
    AnamnesisQuestion("rauchen", "Rauchen Sie derzeit?", input_type="ja_nein"),
    AnamnesisQuestion("alkohol_konsum", "Trinken Sie Alkohol?", input_type="ja_nein"),
    AnamnesisQuestion("alkohol", "Wie häufig und wie viel Alkohol trinken Sie ungefähr?", required=False),
    AnamnesisQuestion("alltag_belastung", "Fällt es Ihnen momentan schwer, mit Ihrem Diabetes im Alltag zurechtzukommen?", input_type="ja_nein"),
    AnamnesisQuestion("stimmung", "Waren Sie in den vergangenen Wochen häufig niedergeschlagen oder hatten wenig Freude an Dingen?", input_type="ja_nein"),
    AnamnesisQuestion("hilfebedarf", "Gibt es Probleme beim Sehen, Erinnern, Verstehen oder beim Benutzen Ihrer Medikamente und Messgeräte?", input_type="ja_nein"),
    AnamnesisQuestion("offene_fragen", "Welche Fragen möchten Sie heute mit Ihrer Ärztin oder Ihrem Arzt besprechen?"),
]


def should_ask_follow_up(question_key: str, answers: dict[str, str]) -> bool:
    follow_ups = {
        "hypo_hyper_beschwerden": "hypo_hyper_hinweise",
        "gewichtsveraenderung_details": "gewichtsveraenderung",
        "blutdruck_zu_hause_details": "blutdruck_zu_hause",
        "folgeerkrankungen_details": "folgeerkrankungen_bekannt",
        "offene_wunde_fussproblem_details": "offene_wunde_fussproblem",
        "hba1c_wert": "hba1c_bekannt",
        "blutzuckerwert_details": "blutzuckerwert_bekannt",
        "alkohol": "alkohol_konsum",
    }
    parent_key = follow_ups.get(question_key)
    if parent_key:
        return _ja(answers.get(parent_key, ""))
    if question_key == "gewicht_messen":
        return _unbekannt(answers.get("gewicht_aktuell", ""))
    if question_key == "blutdruck_messen":
        return _unbekannt(answers.get("blutdruck_systolisch", "")) or _unbekannt(
            answers.get("blutdruck_diastolisch", "")
        )
    return True


def berechne_diabetes_verlaufsuebersicht(
    answers: dict[str, str],
    vitals: dict[str, int | float],
) -> dict[str, str]:
    verlauf: list[str] = []
    symptome: list[str] = []
    komplikationen: list[str] = []
    vorbefunde: list[str] = []

    gewicht = answers.get("gewicht_aktuell", "").strip()
    if not gewicht or _unbekannt(gewicht):
        gewicht = str(vitals.get("gewicht", ""))
    if gewicht:
        verlauf.append(f"Aktuelles Gewicht: {gewicht} kg")

    if _ja(answers.get("gewichtsveraenderung", "")):
        details = answers.get("gewichtsveraenderung_details", "").strip() or "Gewichtsveränderung angegeben"
        verlauf.append(f"Gewichtsveränderung: {details}")

    syst = answers.get("blutdruck_systolisch", "").strip()
    diast = answers.get("blutdruck_diastolisch", "").strip()
    if not syst or _unbekannt(syst):
        syst = str(vitals.get("systolisch", "unbekannt"))
    if not diast or _unbekannt(diast):
        diast = str(vitals.get("diastolisch", "unbekannt"))
    verlauf.append(f"Blutdruck: {syst}/{diast} mmHg")

    symptom_labels = {
        "starker_durst": "ungewöhnlich starker Durst",
        "haeufiges_wasserlassen": "häufigeres Wasserlassen",
        "muedigkeit_schwaeche": "Müdigkeit, Schwäche oder Benommenheit",
        "hypo_hyper_hinweise": "Zittern, Schwitzen, Herzklopfen, Hunger oder Schwindel",
        "akutes_erbrechen_atmung": "Erbrechen, Bauchschmerzen oder auffällige Atmung",
        "akut_verwirrt_bewusstlos": "Verwirrtheit, Ohnmacht oder Bewusstlosigkeit",
        "brustschmerz": "Brustschmerz oder Druck in der Brust",
        "atemnot": "Atemnot",
        "sehstoerungen": "plötzliche Sehverschlechterung",
    }
    symptome.extend(label for key, label in symptom_labels.items() if _ja(answers.get(key, "")))
    details = answers.get("hypo_hyper_beschwerden", "").strip()
    if details:
        symptome.append(details)

    if _ja(answers.get("folgeerkrankungen_bekannt", "")):
        komplikationen.append(answers.get("folgeerkrankungen_details", "").strip() or "bekannte Folgeprobleme angegeben")
    if _ja(answers.get("offene_wunde_fussproblem", "")):
        komplikationen.append(answers.get("offene_wunde_fussproblem_details", "").strip() or "Fußproblem oder Wunde angegeben")
    if _ja(answers.get("gefuehlsstoerungen_fuesse", "")):
        komplikationen.append("Kribbeln, Brennen, Schmerzen oder Taubheit an Füßen/Beinen")

    if _ja(answers.get("hba1c_bekannt", "")):
        vorbefunde.append(f"Langzeit-Blutzuckerwert: {answers.get('hba1c_wert', '').strip() or 'nicht genauer angegeben'}")
    if _ja(answers.get("blutzuckerwert_bekannt", "")):
        vorbefunde.append(f"Letzter Blutzuckerwert: {answers.get('blutzuckerwert_details', '').strip() or 'nicht genauer angegeben'}")
    for key, label in (
        ("letzte_kontrolle", "Letzte Diabetes-Kontrolle"),
        ("letzte_augenkontrolle", "Letzte Augenkontrolle"),
        ("letzte_fusskontrolle", "Letzte Fußkontrolle"),
        ("letzte_nierenkontrolle", "Letzte Nierenkontrolle"),
    ):
        value = answers.get(key, "").strip()
        if value:
            vorbefunde.append(f"{label}: {value}")

    return {
        "verlauf": "; ".join(verlauf) if verlauf else "keine Angaben",
        "symptome": "; ".join(symptome) if symptome else "keine aktuellen Beschwerden angegeben",
        "komplikationen": "; ".join(komplikationen) if komplikationen else "keine bekannten Folgeprobleme angegeben",
        "vorbefunde": "; ".join(vorbefunde) if vorbefunde else "keine Vorbefunde angegeben",
        "hinweis": (
            "Die Verlaufsübersicht dient ausschließlich der strukturierten Dokumentation "
            "für ärztliches Personal. Es erfolgt keine Diagnose, Therapieempfehlung oder Entwarnung."
        ),
    }


def _ja(value: str) -> bool:
    return (value or "").strip().lower() in ("ja", "j", "yes", "y")


def _unbekannt(value: str) -> bool:
    return (value or "").strip().lower() in ("", "unbekannt")
