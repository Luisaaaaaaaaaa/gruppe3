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
SCENARIO_TITLE = "Szenario C: Hypertonie-Kontrolle / auffälliger Blutdruckwert"

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
        key="blutdruck_messen",
        text="Bitte messen Sie Ihren Blutdruck.",
        required=False,
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="puls",
        text="Kennen Sie Ihren aktuellen Puls (Schläge pro Minute)? Falls unbekannt, 'unbekannt' eingeben.",
        input_type="zahl",
        slider_min=50,
        slider_max=250,
        slider_step=1,
    ),
    AnamnesisQuestion(
        key="puls_messen",
        text="Bitte messen Sie Ihren Puls.",
        required=False,
        input_type="freitext",
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
        text="Haben Sie aktuell Brustschmerzen oder ein Druckgefühl im Brustbereich?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="atemnot",
        text="Haben Sie aktuell Atemnot oder Kurzatmigkeit?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="neurologische_symptome",
        text="Haben Sie neurologische Beschwerden wie Taubheitsgefühl, Lähmungen, Sprachstörungen oder Schwindel?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="sehstoerungen",
        text="Haben Sie aktuell Sehstörungen (z.B. verschwommenes Sehen, Flimmern)?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="vorerkrankungen",
        text="Welche Vorerkrankungen sind bei Ihnen bekannt? (z.B. Herz-Kreislauf, Diabetes, Niere)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="lebensstil",
        text="Wie würden Sie Ihren Lebensstil beschreiben? (Bewegung, Ernährung, Stress, Rauchen, Alkohol)",
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
