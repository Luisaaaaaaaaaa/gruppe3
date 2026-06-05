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
SCENARIO_TITLE = "Szenario C: Hypertonie-Kontrolle / auffaelliger Blutdruckwert"

QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion(
        key="blutdruck_systolisch",
        text="Wie hoch war Ihr letzter gemessener Blutdruck (systolischer Wert, oberer Wert)?",
        input_type="zahl",
        slider_min=80,
        slider_max=250,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="blutdruck_diastolisch",
        text="Und der untere Wert (diastolisch)?",
        input_type="zahl",
        slider_min=40,
        slider_max=150,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="puls",
        text="Kennen Sie Ihren aktuellen Puls (Schlaege pro Minute)? Falls unbekannt, 'unbekannt' eingeben.",
        input_type="zahl",
        slider_min=50,
        slider_max=250,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="messbedingungen",
        text="Unter welchen Bedingungen wurde gemessen? (z.B. in Ruhe, nach Belastung, morgens, abends)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="kopfschmerz",
        text="Haben Sie aktuell Kopfschmerzen?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="brustschmerz",
        text="Haben Sie aktuell Brustschmerzen oder ein Druckgefuehl im Brustbereich?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="atemnot",
        text="Haben Sie aktuell Atemnot oder Kurzatmigkeit?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="neurologische_symptome",
        text="Haben Sie neurologische Beschwerden wie Taubheitsgefuehl, Laehmungen, Sprachstoerungen oder Schwindel?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="sehstoerungen",
        text="Haben Sie aktuell Sehstoerungen (z.B. verschwommenes Sehen, Flimmern)?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="vorerkrankungen",
        text="Welche Vorerkrankungen sind bei Ihnen bekannt? (z.B. Herz-Kreislauf, Diabetes, Niere)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="medikamente",
        text="Welche Medikamente nehmen Sie aktuell ein?",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="adhaerenz",
        text="Nehmen Sie Ihre Medikamente regelmaessig ein?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="lebensstil",
        text="Wie wuerden Sie Ihren Lebensstil beschreiben? (Bewegung, Ernaehrung, Stress, Rauchen, Alkohol)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="risikofaktoren",
        text="Gibt es in Ihrer Familie Herz-Kreislauf-Erkrankungen oder andere Risikofaktoren?",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="gewicht",
        text="Wie viel wiegen Sie aktuell (in kg)? Falls unbekannt, 'unbekannt' eingeben.",
        input_type="zahl",
        slider_min=30,
        slider_max=300,
        slider_step=1,
    ),
]
