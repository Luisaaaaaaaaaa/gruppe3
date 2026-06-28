from app.scenarios.hypertension_scenario import AnamnesisQuestion

SCENARIO_KEY = "cough"
SCENARIO_TITLE = "Szenario A: Akuter Husten / Atemwegsinfekt / Verdacht auf Pneumonie"

# Medizinische Grundlage: DEGAM-Leitlinie Husten (AWMF 053-013),
# S3-Leitlinie ambulant erworbene Pneumonie (AWMF 020-020) und Projektvorgaben.
# Der Dialog erhebt nur Angaben und Warnzeichen; er stellt keine Diagnose.


QUESTIONS: list[AnamnesisQuestion] = [
    AnamnesisQuestion("symptom_dauer", "Wie lange haben Sie schon Husten oder andere Beschwerden? (z. B. seit 2 Tagen)"),
    AnamnesisQuestion("rasche_verschlechterung", "Sind Ihre Beschwerden in den letzten Stunden deutlich schlimmer geworden?", input_type="ja_nein"),
    AnamnesisQuestion("hustenart", "Wie fühlt sich Ihr Husten an? (z. B. trocken, kratzend, bellend oder sehr stark)"),
    AnamnesisQuestion("auswurf", "Kommt beim Husten Schleim mit?", input_type="ja_nein"),
    AnamnesisQuestion("auswurf_farbe", "Welche Farbe hat der Schleim? (z. B. klar, weiß, gelb, grün, braun oder rötlich)"),
    AnamnesisQuestion("blutbeimengung", "Haben Sie beim Husten Blut bemerkt?", input_type="ja_nein"),
    AnamnesisQuestion("fieber", "Haben Sie Fieber?", input_type="ja_nein"),
    AnamnesisQuestion("korpertemperatur", "Wie hoch war Ihre höchste gemessene Temperatur? Schreiben Sie 'nicht gemessen', falls Sie es nicht wissen."),
    AnamnesisQuestion("schuettelfrost", "Hatten Sie starkes Zittern vor Kälte, obwohl Ihnen gleichzeitig heiß war?", input_type="ja_nein"),
    AnamnesisQuestion("dyspnoe", "Bekommen Sie schlechter Luft als sonst oder sind Sie ungewöhnlich kurzatmig?", input_type="ja_nein"),
    AnamnesisQuestion("ruhedyspnoe", "Bekommen Sie auch im Sitzen oder Liegen schlecht Luft?", input_type="ja_nein"),
    AnamnesisQuestion("sprechen_beeintraechtigt", "Müssen Sie beim Sprechen nach wenigen Worten Luft holen?", input_type="ja_nein"),
    AnamnesisQuestion("belastungsdyspnoe", "Bekommen Sie bei kleinen Anstrengungen, zum Beispiel beim Gehen oder Treppensteigen, schlechter Luft als sonst?", input_type="ja_nein"),
    AnamnesisQuestion("zyanose", "Sind Ihre Lippen oder Ihr Gesicht bläulich verfärbt?", input_type="ja_nein"),
    AnamnesisQuestion("auffaelliges_atemgeraeusch", "Hören Sie beim Einatmen ein neues lautes, pfeifendes oder ziehendes Geräusch?", input_type="ja_nein"),
    AnamnesisQuestion(
        "spo2",
        "Falls eine Pulsoximetrie durchgefuehrt wurde: Wie hoch ist die Sauerstoffsaettigung in Prozent?",
        input_type="zahl",
        slider_min=70,
        slider_max=100,
        slider_step=1,
        required=False,
    ),
    AnamnesisQuestion("thorakale_schmerzen", "Haben Sie Schmerzen oder Druck in der Brust?", input_type="ja_nein"),
    AnamnesisQuestion("atemabhaengige_schmerzen", "Werden die Schmerzen beim tiefen Einatmen oder Husten stärker?", input_type="ja_nein"),
    AnamnesisQuestion("verwirrtheit", "Fühlen Sie sich plötzlich verwirrt oder können Sie sich ungewöhnlich schlecht orientieren?", input_type="ja_nein"),
    AnamnesisQuestion("ohnmacht", "Sind Sie seit Beginn der Beschwerden ohnmächtig geworden oder beinahe zusammengebrochen?", input_type="ja_nein"),
    AnamnesisQuestion("reduzierter_allgemeinzustand", "Fühlen Sie sich so schwach oder krank, dass Sie Ihren Alltag kaum bewältigen können?", input_type="ja_nein"),
    AnamnesisQuestion("rauch_reizstoffe", "Haben Sie kurz vor Beginn der Beschwerden Rauch, Brandgase oder reizende Dämpfe eingeatmet?", input_type="ja_nein"),
    AnamnesisQuestion("brustverletzung", "Hatten Sie in letzter Zeit eine Verletzung am Brustkorb, zum Beispiel durch einen Sturz oder Unfall?", input_type="ja_nein"),
    AnamnesisQuestion("chronische_lungenerkrankung", "Haben Sie eine dauerhafte Erkrankung der Lunge, zum Beispiel Asthma oder eine chronisch verengte Lunge?", input_type="ja_nein"),
    AnamnesisQuestion("herzschwaeche", "Ist bei Ihnen eine Herzschwäche bekannt?", input_type="ja_nein"),
    AnamnesisQuestion("immunschwaeche", "Ist Ihre Abwehr stark geschwächt, zum Beispiel durch eine Organtransplantation, Krebsbehandlung oder bestimmte Medikamente?", input_type="ja_nein"),
    AnamnesisQuestion("vorerkrankungen", "Welche länger bestehenden Erkrankungen sind bei Ihnen bekannt? Schreiben Sie 'keine', wenn keine bekannt sind."),
    AnamnesisQuestion("risikofaktoren", "Rauchen Sie oder gab es kürzlich eine Reise beziehungsweise engen Kontakt zu Menschen mit einem Atemwegsinfekt? Bitte kurz beschreiben."),
    AnamnesisQuestion("atemfrequenz", "Falls Ihre Atemzüge eine Minute lang gezählt wurden: Wie viele waren es? Sonst können Sie 'nicht gemessen' schreiben.", required=False),
]


PULSOXIMETER_TRIGGER_KEYS = {
    "blutbeimengung",
    "dyspnoe",
    "ruhedyspnoe",
    "sprechen_beeintraechtigt",
    "belastungsdyspnoe",
    "zyanose",
    "auffaelliges_atemgeraeusch",
    "thorakale_schmerzen",
    "verwirrtheit",
    "ohnmacht",
    "reduzierter_allgemeinzustand",
    "rauch_reizstoffe",
    "rasche_verschlechterung",
    "chronische_lungenerkrankung",
    "herzschwaeche",
    "immunschwaeche",
}


def should_offer_pulsoximeter(answers: dict[str, str]) -> bool:
    """Pulsoximetry is offered only when respiratory warning signs justify it."""
    return any(
        (answers.get(key) or "").strip().lower() in ("ja", "j", "yes", "y")
        for key in PULSOXIMETER_TRIGGER_KEYS
    )
