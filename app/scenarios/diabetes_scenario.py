from app.scenarios.hypertension_scenario import AnamnesisQuestion


SCENARIO_KEY = "diabetes"
SCENARIO_TITLE = "Szenario D: Typ-2-Diabetes / metabolische Verlaufskontrolle"

QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion(
        key="bekannte_diagnosen",
        text=(
            "Welche bekannten Diagnosen oder Vorerkrankungen liegen bei Ihnen vor? "
            "(z.B. Typ-2-Diabetes, Bluthochdruck, Fettstoffwechselstörung, Nierenerkrankung)"
        ),
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="hypo_hyper_hinweise",
        text=(
            "Haben Sie aktuell Hinweise auf eine Unterzuckerung oder Überzuckerung? "
            "(z.B. Zittern, Schweißausbruch, Schwindel, Sehstörungen, starker Durst, "
            "häufiges Wasserlassen, Müdigkeit)"
        ),
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="hypo_hyper_beschwerden",
        text="Welche Beschwerden genau haben Sie aktuell?",
        input_type="freitext",
        required=False,
    ),
    AnamnesisQuestion(
        key="gewicht_aktuell",
        text="Wie viel wiegen Sie aktuell in kg? Falls unbekannt, 'unbekannt' eingeben.",
        input_type="zahl",
        slider_min=30,
        slider_max=300,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="gewichtsveraenderung",
        text="Hat sich Ihr Gewicht in letzter Zeit verändert?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="gewichtsveraenderung_details",
        text="Bitte beschreiben Sie die Gewichtsveränderung. Zu- oder Abnahme und ungefähr wie viel kg?",
        input_type="freitext",
        required=False,
    ),
    AnamnesisQuestion(
        key="blutdruck_systolisch",
        text="Wie hoch war Ihr letzter systolischer Blutdruckwert (oberer Wert), falls bekannt? Falls unbekannt, 'unbekannt' eingeben.",
        input_type="zahl",
        slider_min=80,
        slider_max=250,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="blutdruck_diastolisch",
        text="Wie hoch war Ihr letzter diastolischer Blutdruckwert (unterer Wert), falls bekannt? Falls unbekannt, 'unbekannt' eingeben.",
        input_type="zahl",
        slider_min=40,
        slider_max=150,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="lebensstil",
        text=(
            "Wie würden Sie Ihren Lebensstil beschreiben? "
            "(Ernährung, Bewegung, Rauchen, Alkohol, Stress)"
        ),
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="folgeerkrankungen_bekannt",
        text=(
            "Sind bei Ihnen Folgeerkrankungen oder bekannte Komplikationen des Diabetes bekannt? "
            "(z.B. Nierenerkrankung, Augenerkrankung, Neuropathie, diabetischer Fuß, "
            "Herz-Kreislauf-Erkrankung)"
        ),
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="folgeerkrankungen_details",
        text=(
            "Welche Folgeerkrankungen oder Komplikationen sind bekannt? "
            "(z.B. Niere, Auge, Nerven, diabetischer Fuß, Herz-Kreislauf)"
        ),
        input_type="freitext",
        required=False,
    ),
    AnamnesisQuestion(
        key="offene_wunde_fussproblem",
        text="Haben Sie offene Wunden, Druckstellen oder andere Probleme an den Fuessen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="offene_wunde_fussproblem_details",
        text="Seit wann besteht das Fußproblem oder die Wunde, und hat es sich verschlechtert?",
        input_type="freitext",
        required=False,
    ),
    AnamnesisQuestion(
        key="hba1c_bekannt",
        text="Ist Ihnen Ihr letzter HbA1c-Wert bekannt?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="hba1c_wert",
        text="Wie hoch war Ihr letzter HbA1c-Wert?",
        input_type="freitext",
        required=False,
    ),
    AnamnesisQuestion(
        key="blutzuckerwert_bekannt",
        text="Ist Ihnen ein letzter Blutzuckerwert bekannt?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="blutzuckerwert_details",
        text=(
            "Bitte geben Sie den letzten bekannten Blutzuckerwert an "
            "(z.B. nüchtern 145 mg/dl oder nach dem Essen 180 mg/dl)."
        ),
        input_type="freitext",
        required=False,
    ),
    AnamnesisQuestion(
        key="letzte_kontrolle",
        text="Wann war Ihre letzte Diabetes-Kontrolle?",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="offene_fragen",
        text="Welche offenen Fragen haben Sie an das ärztliche Personal?",
        input_type="freitext",
    ),
]


def should_ask_follow_up(question_key: str, answers: dict[str, str]) -> bool:
    if question_key == "hypo_hyper_beschwerden":
        return _ja(answers.get("hypo_hyper_hinweise", ""))
    if question_key == "gewichtsveraenderung_details":
        return _ja(answers.get("gewichtsveraenderung", ""))
    if question_key == "folgeerkrankungen_details":
        return _ja(answers.get("folgeerkrankungen_bekannt", ""))
    if question_key == "offene_wunde_fussproblem_details":
        return _ja(answers.get("offene_wunde_fussproblem", ""))
    if question_key == "hba1c_wert":
        return _ja(answers.get("hba1c_bekannt", ""))
    if question_key == "blutzuckerwert_details":
        return _ja(answers.get("blutzuckerwert_bekannt", ""))
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
    if gewicht:
        verlauf.append(f"Aktuelles Gewicht: {gewicht}")

    if _ja(answers.get("gewichtsveraenderung", "")):
        details = answers.get("gewichtsveraenderung_details", "").strip() or "Gewichtsveraenderung angegeben"
        verlauf.append(f"Gewichtsveraenderung: {details}")

    syst = answers.get("blutdruck_systolisch", "").strip() or str(vitals.get("systolisch", "unbekannt"))
    diast = answers.get("blutdruck_diastolisch", "").strip() or str(vitals.get("diastolisch", "unbekannt"))
    verlauf.append(f"Blutdruck: {syst}/{diast} mmHg")

    if _ja(answers.get("hypo_hyper_hinweise", "")):
        symptome.append(
            answers.get("hypo_hyper_beschwerden", "").strip()
            or "Hinweise auf Hypo-/Hyperglykämie wurden angegeben"
        )

    if _ja(answers.get("folgeerkrankungen_bekannt", "")):
        komplikationen.append(
            answers.get("folgeerkrankungen_details", "").strip()
            or "Folgeerkrankungen oder Komplikationen wurden angegeben"
        )

    if _ja(answers.get("offene_wunde_fussproblem", "")):
        komplikationen.append(
            answers.get("offene_wunde_fussproblem_details", "").strip()
            or "Fussproblem oder Wunde angegeben"
        )

    if _ja(answers.get("hba1c_bekannt", "")):
        vorbefunde.append(
            f"HbA1c: {answers.get('hba1c_wert', '').strip() or 'bekannt, aber nicht genauer angegeben'}"
        )

    if _ja(answers.get("blutzuckerwert_bekannt", "")):
        vorbefunde.append(
            "Letzter Blutzuckerwert: "
            f"{answers.get('blutzuckerwert_details', '').strip() or 'bekannt, aber nicht genauer angegeben'}"
        )

    letzte_kontrolle = answers.get("letzte_kontrolle", "").strip()
    if letzte_kontrolle:
        vorbefunde.append(f"Letzte Diabetes-Kontrolle: {letzte_kontrolle}")

    return {
        "verlauf": "; ".join(verlauf) if verlauf else "keine Angaben",
        "symptome": "; ".join(symptome) if symptome else "keine aktuellen Hinweise dokumentiert",
        "komplikationen": "; ".join(komplikationen) if komplikationen else "keine bekannten Komplikationen dokumentiert",
        "vorbefunde": "; ".join(vorbefunde) if vorbefunde else "keine Vorbefunde dokumentiert",
        "hinweis": (
            "Die Verlaufsübersicht dient ausschließlich der strukturierten Dokumentation "
            "für ärztliches Personal. Es erfolgt keine Diagnose, Therapieempfehlung oder Entwarnung."
        ),
    }


def _ja(value: str) -> bool:
    return (value or "").strip().lower() in ("ja", "j", "yes", "y")
