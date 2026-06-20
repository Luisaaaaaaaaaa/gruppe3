from app.scenarios.hypertension_scenario import AnamnesisQuestion


SCENARIO_KEY = "chest_pain"
SCENARIO_TITLE = "Szenario B: Brustschmerz in der Hausarztpraxis"

# Medizinische Grundlage: DEGAM-Leitlinie Brustschmerz (Kurzfassung),
# Marburger Herzscore und Vorgaben des Semesterprojekts. Der Fragebogen
# dokumentiert Beschwerden und Warnzeichen; er stellt keine Diagnose.

QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion(
        "lokalisation",
        (
            "WICHTIG: Haben Sie gerade starke Schmerzen, schlecht Luft, kalten Schweiß, "
            "starke Schwäche oder waren Sie beinahe ohnmächtig? Informieren Sie bitte "
            "sofort das Praxispersonal.\n\nWo genau spüren Sie die Schmerzen? "
            "(z. B. Mitte der Brust, links, rechts oder an mehreren Stellen)"
        ),
    ),
    AnamnesisQuestion(
        "beginn",
        "Wann haben die Schmerzen begonnen? (z. B. heute vor 2 Stunden oder seit gestern)",
    ),
    AnamnesisQuestion(
        "ploetzlicher_beginn",
        "Haben die Schmerzen plötzlich begonnen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "dauer",
        (
            "Wie lange halten die Schmerzen jeweils an? "
            "(z. B. wenige Sekunden, einige Minuten, länger als 20 Minuten oder dauerhaft)"
        ),
    ),
    AnamnesisQuestion(
        "schmerzen_aktuell",
        "Haben Sie die Schmerzen gerade jetzt?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "schmerzstaerke",
        "Wie stark sind die Schmerzen gerade? 0 bedeutet keine Schmerzen, 10 die stärksten vorstellbaren Schmerzen.",
        input_type="zahl",
        slider_min=0,
        slider_max=10,
        slider_step=1,
    ),
    AnamnesisQuestion(
        "schmerzcharakter",
        "Wie fühlen sich die Schmerzen an? (z. B. Druck, Enge, Brennen, Stechen oder Ziehen)",
    ),
    AnamnesisQuestion(
        "ausstrahlung",
        (
            "Ziehen die Schmerzen in eine andere Körperstelle? "
            "(z. B. linker oder rechter Arm, beide Arme, Hals, Unterkiefer, Rücken, Oberbauch oder nirgendwohin)"
        ),
    ),
    AnamnesisQuestion(
        "belastungsabhaengigkeit",
        "Beginnen oder verstärken sich die Schmerzen bei Anstrengung, zum Beispiel beim Gehen oder Treppensteigen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "ruhe_besserung",
        "Werden die Schmerzen besser, wenn Sie sich ausruhen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "bewegung_atmung_husten",
        "Werden die Schmerzen stärker, wenn Sie sich bewegen, tief einatmen oder husten?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "druckschmerz_thoraxwand",
        "Können Sie die Schmerzen durch Druck auf die schmerzende Stelle auslösen oder verstärken?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "essen_schlucken",
        "Hängen die Schmerzen mit Essen oder Schlucken zusammen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "sodbrennen",
        "Haben Sie gleichzeitig Sodbrennen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "uebelkeit",
        "Ist Ihnen übel oder mussten Sie erbrechen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "atemnot",
        "Bekommen Sie schlechter Luft als sonst?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "ruhedyspnoe",
        "Bekommen Sie auch im Sitzen oder Liegen schlecht Luft?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "kaltschweissigkeit",
        "Haben Sie ungewöhnlich stark oder kalt geschwitzt?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "synkope",
        "Sind Sie seit Beginn der Schmerzen ohnmächtig geworden oder beinahe zusammengebrochen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "verwirrtheit",
        "Fühlen Sie sich plötzlich verwirrt, sehr benommen oder ungewöhnlich schlecht orientiert?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "ausgepraege_schwaeche",
        "Fühlen Sie sich so schwach oder krank, dass Sie Ihren Alltag kaum bewältigen können?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "rasche_verschlechterung",
        "Sind die Schmerzen oder andere Beschwerden in den letzten 24 Stunden stärker oder häufiger geworden?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "aehnliche_schmerzen",
        "Hatten Sie schon einmal ähnliche Schmerzen? Falls ja: Was war damals die Ursache?",
    ),
    AnamnesisQuestion(
        "patient_vermutet_herz",
        "Glauben Sie selbst, dass die Schmerzen vom Herzen kommen könnten?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "bekannte_khk",
        (
            "Ist bei Ihnen eine Erkrankung des Herzens oder der Blutgefäße bekannt, "
            "zum Beispiel ein früherer Herzinfarkt, Schlaganfall oder verengte Blutgefäße?"
        ),
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "kardiovaskulaere_risikofaktoren",
        (
            "Trifft etwas davon auf Sie zu: Rauchen, hoher Blutdruck, Zuckerkrankheit, "
            "hohe Blutfettwerte, starkes Übergewicht oder frühe Herzerkrankungen bei Eltern oder Geschwistern? "
            "Schreiben Sie bitte alles Zutreffende auf oder 'nichts davon'."
        ),
    ),
    AnamnesisQuestion(
        "vorerkrankungen",
        "Welche anderen länger bestehenden Krankheiten haben Sie? Schreiben Sie 'keine', wenn keine bekannt sind.",
    ),
]


def berechne_marburger_herzscore(
    answers: dict[str, str],
    *,
    alter: int | None = None,
    geschlecht: str = "",
) -> dict[str, int | str]:
    """Dokumentiert die fünf Originalkriterien des Marburger Herzscores."""
    score = 0
    details: list[str] = []

    geschlecht_normalisiert = geschlecht.strip().lower()
    alterskriterium = (
        alter is not None
        and (
            (geschlecht_normalisiert in ("m", "maennlich", "männlich", "male") and alter >= 55)
            or (geschlecht_normalisiert in ("w", "weiblich", "female") and alter >= 65)
        )
    )
    if alterskriterium:
        score += 1
        details.append("Alters- und Geschlechtskriterium erfüllt (+1)")

    if _ja(answers.get("bekannte_khk", "")):
        score += 1
        details.append("Bekannte Erkrankung der Blutgefäße (+1)")

    if _ja(answers.get("belastungsabhaengigkeit", "")):
        score += 1
        details.append("Schmerzen bei Anstrengung (+1)")

    if _nein(answers.get("druckschmerz_thoraxwand", "")):
        score += 1
        details.append("Schmerz durch Druck nicht auslösbar (+1)")

    if _ja(answers.get("patient_vermutet_herz", "")):
        score += 1
        details.append("Patient vermutet das Herz als Ursache (+1)")

    return {
        "score": score,
        "max_score": 5,
        "details": ", ".join(details) if details else "kein Kriterium erfüllt",
        "einordnung": "Nur ärztlich und zusammen mit der gesamten Untersuchung zu bewerten.",
        "hinweis": (
            "Der Marburger Herzscore ersetzt weder die Suche nach Warnzeichen noch die "
            "ärztliche Untersuchung. Er darf nicht zur Entwarnung verwendet werden."
        ),
    }


def _ja(value: str) -> bool:
    return value.strip().lower() in ("ja", "j", "yes", "y")


def _nein(value: str) -> bool:
    return value.strip().lower() in ("nein", "n", "no")
