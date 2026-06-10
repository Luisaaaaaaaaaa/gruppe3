from dataclasses import dataclass

from app.scenarios.hypertension_scenario import AnamnesisQuestion


SCENARIO_KEY = "chest_pain"
SCENARIO_TITLE = "Szenario B: Brustschmerz in der Hausarztpraxis"

QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion(
        key="lokalisation",
        text="Wo genau spueren Sie die Schmerzen? (z.B. hinter dem Brustbein, links, rechts, grossflaechig)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="beginn",
        text="Wann haben die Schmerzen begonnen? (z.B. vor 2 Stunden, seit gestern)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="dauer",
        text="Wie lange halten die Schmerzen an? (z.B. wenige Sekunden, Minuten, dauerhaft)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="schmerzcharakter",
        text="Wie wuerden Sie den Schmerz beschreiben? (z.B. drückend, stechend, brennend, eng)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="ausstrahlung",
        text="Strahlt der Schmerz aus? (z.B. in den linken Arm, Kiefer, Ruecken, Bauch, oder keine Ausstrahlung)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="belastungsabhaengigkeit",
        text="Treten die Schmerzen bei koerperlicher Belastung auf oder verstaerken sie sich dabei?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="ruhe_besserung",
        text="Bessern sich die Schmerzen in Ruhe?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="atemnot",
        text="Haben Sie aktuell Atemnot oder Kurzatmigkeit?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="uebelkeit",
        text="Haben Sie Uebelkeit oder mussten Sie erbrechen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="kaltschweissigkeit",
        text="Schwitzen Sie ungewoehnlich oder haben Sie Kaltschweissigkeit bemerkt?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="synkope",
        text="Hatten Sie eine Ohnmacht oder das Gefuehl, gleich ohnmaechtig zu werden?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="ausgepraege_schwaeche",
        text="Fuehlen Sie sich ungewoehnlich schwach oder erschoepft?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="bekannte_khk",
        text="Ist bei Ihnen eine Herzerkrankung bekannt (z.B. koronare Herzkrankheit, frueherer Herzinfarkt)?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="alter_ueber_55",
        text="Sind Sie aelter als 55 Jahre?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="kardiovaskulaere_risikofaktoren",
        text="Welche Risikofaktoren liegen bei Ihnen vor? (z.B. Rauchen, Diabetes, Bluthochdruck, hohe Cholesterinwerte, Uebergewicht, Familienanamnese)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="vorerkrankungen",
        text="Welche weiteren Vorerkrankungen sind bei Ihnen bekannt?",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="druckschmerz_thoraxwand",
        text="Ist der Schmerz durch Druck auf die Brustwand reproduzierbar?",
        input_type="ja_nein",
    ),
]


# --- Marburger Herzscore (didaktische Annaeherung) ---
# Quelle: Bosner et al., DEGAM-Leitlinie Brustschmerz
# ACHTUNG: Keine Diagnose, keine Entwarnung, keine Risikobewertung.
# Dient ausschliesslich der strukturierten Dokumentation fuer aerztliches Personal.

def berechne_marburger_herzscore(answers: dict[str, str]) -> dict[str, int | str]:
    score = 0
    details: list[str] = []

    if _ja(answers.get("alter_ueber_55", "")):
        # Kriterium 1: Alter/Geschlecht (>=55 bei Maennern, >=65 bei Frauen)
        # Vereinfacht: Alter > 55 als Proxy
        score += 1
        details.append("Alter >55 (+1)")

    if _ja(answers.get("bekannte_khk", "")):
        score += 1
        details.append("Bekannte vaskulaere Erkrankung (+1)")

    if _ja(answers.get("belastungsabhaengigkeit", "")):
        score += 1
        details.append("Belastungsabhaengigkeit (+1)")

    if not _ja(answers.get("druckschmerz_thoraxwand", "")):
        score += 1
        details.append("Schmerz nicht durch Palpation reproduzierbar (+1)")

    # Kriterium 5: Patient vermutet kardiale Ursache (nicht direkt abgefragt,
    # aber Ausstrahlung + Schmerzcharakter als Proxy)
    ausstrahlung = answers.get("ausstrahlung", "").lower()
    if any(kw in ausstrahlung for kw in ("arm", "kiefer", "linke")):
        score += 1
        details.append("Typische Ausstrahlung (+1)")

    risiko_text = "niedrig"
    if score >= 3:
        risiko_text = "erhoehte Wahrscheinlichkeit fuer KHK"
    elif score >= 1:
        risiko_text = "intermediär"

    return {
        "score": score,
        "max_score": 5,
        "details": ", ".join(details) if details else "keine Kriterien erfuellt",
        "einordnung": risiko_text,
        "hinweis": (
            "Der Marburger Herzscore dient ausschliesslich der didaktischen "
            "Strukturierung. Er stellt keine Diagnose und keine Risikobewertung dar. "
            "Die aerztliche Bewertung ist zwingend erforderlich."
        ),
    }


def _ja(value: str) -> bool:
    return value.strip().lower() in ("ja", "j", "yes", "y")
