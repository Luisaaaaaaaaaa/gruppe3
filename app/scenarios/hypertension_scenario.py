from dataclasses import dataclass


@dataclass(frozen=True)
class AnamnesisQuestion:
    key: str
    text: str
    required: bool = True
    input_type: str = "freitext"  # freitext, ja_nein, zahl
    slider_min: float | None = None
    slider_max: float | None = None
    slider_step: float | None = None


SCENARIO_KEY = "hypertension"
SCENARIO_TITLE = "Szenario C: Bluthochdruck-Kontrolle / auffälliger Blutdruckwert"

# Medizinische Grundlage: NVL Hypertonie, Kurzfassung Version 1.0 (2023),
# insbesondere Kapitel 3 (Diagnostik), Kapitel 4 (Kontrolle) und Kapitel 7.5
# (stark erhöhter Blutdruck mit Warnzeichen). Der Dialog sammelt Angaben und
# Messwerte für das Praxisteam; er stellt keine Diagnose.

QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion(
        key="bluthochdruck_bekannt",
        text="Wurde bei Ihnen bereits Bluthochdruck festgestellt?",
        input_type="ja_nein",
    ),
    # Zweig: bekannte Erkrankung / Kontrolltermin
    AnamnesisQuestion(
        key="letzte_kontrolle",
        text="Wann wurde Ihr Blutdruck zuletzt ärztlich kontrolliert?",
    ),
    AnamnesisQuestion(
        key="behandlung_geaendert",
        text="Wurde Ihre Behandlung seit der letzten Kontrolle verändert?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="heimwerte_vorhanden",
        text="Haben Sie in den letzten sieben Tagen zu Hause Blutdruck gemessen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="heimwerte_verlauf",
        text=(
            "Wie waren Ihre Werte zu Hause? Bitte nennen Sie, wenn möglich, "
            "den niedrigsten und höchsten Wert oder zeigen Sie Ihre Aufzeichnungen."
        ),
    ),
    # Zweig: erstmals auffälliger Wert
    AnamnesisQuestion(
        key="auffaelliger_wert_wann",
        text="Wann und wo wurde der auffällige Blutdruckwert gemessen?",
    ),
    AnamnesisQuestion(
        key="mehrfach_gemessen",
        text="Wurde danach noch einmal gemessen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="fruehere_auffaellige_werte",
        text="Gab es bei Ihnen früher schon einmal auffällige Blutdruckwerte?",
        input_type="ja_nein",
    ),
    # Gemeinsame Messwerterfassung. Die Werte können in der Oberfläche durch
    # die Blutdruckmanschetten- und Pulssimulation eingesetzt werden.
    AnamnesisQuestion(
        key="blutdruck_systolisch",
        text="Wie hoch ist der obere Blutdruckwert?",
        input_type="zahl",
        slider_min=80,
        slider_max=250,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="blutdruck_diastolisch",
        text="Wie hoch ist der untere Blutdruckwert?",
        input_type="zahl",
        slider_min=40,
        slider_max=150,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="blutdruck_messen",
        text="Bitte messen Sie jetzt Ihren Blutdruck.",
        required=False,
    ),
    AnamnesisQuestion(
        key="puls",
        text="Wie hoch ist Ihr aktueller Puls?",
        input_type="zahl",
        slider_min=30,
        slider_max=250,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="puls_messen",
        text="Bitte messen Sie jetzt Ihren Puls.",
        required=False,
    ),
    AnamnesisQuestion(
        key="messbedingungen",
        text=(
            "Wie wurde gemessen? Bitte beschreiben Sie kurz, ob Sie vorher mindestens "
            "fünf Minuten ruhig saßen und ob Sie kurz zuvor Sport gemacht, geraucht "
            "oder Kaffee getrunken hatten."
        ),
    ),
    # Aktuelle Beschwerden und Warnzeichen
    AnamnesisQuestion("brustschmerz", "Haben Sie gerade Schmerzen oder starken Druck in der Brust?", input_type="ja_nein"),
    AnamnesisQuestion("atemnot", "Bekommen Sie gerade schlechter Luft als sonst?", input_type="ja_nein"),
    AnamnesisQuestion(
        "neurologische_symptome",
        "Haben Sie plötzlich eine Lähmung, ein Taubheitsgefühl oder Probleme beim Sprechen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "sehstoerungen",
        "Sehen Sie plötzlich verschwommen, doppelt oder deutlich schlechter als sonst?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion("kopfschmerz", "Haben Sie gerade ungewöhnlich starke Kopfschmerzen?", input_type="ja_nein"),
    AnamnesisQuestion(
        "ohnmacht",
        "Sind Sie heute ohnmächtig geworden oder beinahe zusammengebrochen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "herzklopfen",
        "Spüren Sie gerade starkes Herzklopfen oder einen sehr schnellen oder unregelmäßigen Herzschlag?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="vorerkrankungen",
        text=(
            "Welche länger bestehenden Krankheiten sind bei Ihnen bekannt, zum Beispiel "
            "am Herzen, an den Blutgefäßen, an den Nieren oder Zuckerkrankheit? "
            "Schreiben Sie 'keine', wenn keine bekannt sind."
        ),
    ),
    # Lebensweise und mögliche beeinflussende Faktoren
    AnamnesisQuestion(
        "rauchen_alkohol",
        "Rauchen Sie oder trinken Sie regelmäßig Alkohol? Bitte kurz beschreiben.",
    ),
    AnamnesisQuestion(
        "ernaehrung",
        "Essen Sie häufig sehr salzig, viel Lakritz oder trinken Sie viel Kaffee oder Energydrinks?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "bewegung",
        "Bewegen Sie sich an den meisten Tagen mindestens eine halbe Stunde?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "stress",
        "Fühlen Sie sich zurzeit häufig stark angespannt oder belastet?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        "schlaf",
        "Schnarchen Sie laut, wurden Atempausen bemerkt oder sind Sie tagsüber oft ungewöhnlich müde?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="gewicht",
        text="Wie viel wiegen Sie aktuell in Kilogramm?",
        input_type="zahl",
        slider_min=30,
        slider_max=300,
        slider_step=0.1,
    ),
    AnamnesisQuestion(
        key="gewicht_messen",
        text="Bitte wiegen Sie sich jetzt.",
        required=False,
    ),
]
