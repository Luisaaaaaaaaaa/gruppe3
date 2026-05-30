from app.scenarios.hypertension_scenario import AnamnesisQuestion

SCENARIO_KEY = "cough"
SCENARIO_TITLE = "Szenario A: Akuter Husten / Atemwegsinfekt / Verdacht auf Pneumonie"

QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion(
        key="symptom_dauer",
        text="Seit wann haben Sie die Symptome? (z.B. seit 2 Tagen, seit einer Woche)",
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="hustenart",
        text=(
            "Welche Art von Husten haben Sie? "
            "(trockener Reizhusten, produktiver Husten mit Auswurf, "
            "bellender Husten, oder bitte beschreiben)"
        ),
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="fieber",
        text="Haben Sie Fieber oder Sch\u00fcttelfrost?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="dyspnoe",
        text="Haben Sie Atemnot oder Kurzatmigkeit?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="belastungsdyspnoe",
        text="Haben Sie Atemnot bei Belastung (z.B. Treppensteigen)?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="auswurf_farbe",
        text=(
            "Haben Sie Auswurf beim Husten? Wenn ja: welche Farbe hat er? "
            "(klar/wei\u00df, gelb/gr\u00fcn, braun, blutig, oder bitte beschreiben)"
        ),
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="blutbeimengung",
        text="Ist Blut im Auswurf?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="thorakale_schmerzen",
        text="Haben Sie Schmerzen im Brustbereich?",
        input_type="ja_nein",
    ),
    AnamnesisQuestion(
        key="vorerkrankungen",
        text=(
            "Liegen bei Ihnen Vorerkrankungen vor? "
            "(z.B. Asthma, COPD, Herzinsuffizienz, Immunsuppression, oder andere)"
        ),
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="risikofaktoren",
        text=(
            "Bestehen relevante Risikofaktoren? "
            "(z.B. Rauchen, hohes Alter, berufliche Exposition, "
            "k\u00fcrzliche Reisen, Kontakt zu Infizierten)"
        ),
        input_type="freitext",
    ),
    AnamnesisQuestion(
        key="medikamente",
        text="Welche Medikamente nehmen Sie aktuell ein?",
        input_type="freitext",
    ),
]
