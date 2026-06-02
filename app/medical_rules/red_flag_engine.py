from dataclasses import dataclass


@dataclass(frozen=True)
class RedFlag:
    rule_id: str
    description: str
    severity: str  # "warning" or "critical"
    triggered_by: str


def _parse_ja_nein(value: str) -> bool:
    return value.strip().lower() in ("ja", "j", "yes", "y")


def _parse_number(value: str) -> float | None:
    try:
        return float(value.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None


def check_hypertension(answers: dict[str, str], vitals: dict[str, int | float] | None = None) -> list[RedFlag]:
    flags: list[RedFlag] = []

    sys_val = _parse_number(answers.get("blutdruck_systolisch", ""))
    dia_val = _parse_number(answers.get("blutdruck_diastolisch", ""))

    if vitals:
        sys_val = sys_val or vitals.get("systolisch")
        dia_val = dia_val or vitals.get("diastolisch")

    if sys_val is not None and sys_val >= 180:
        flags.append(RedFlag(
            rule_id="HYP-RF-001",
            description="Systolischer Blutdruck >= 180 mmHg: Hypertensiver Notfall moeglich.",
            severity="critical",
            triggered_by=f"systolisch={int(sys_val)}",
        ))

    if dia_val is not None and dia_val >= 120:
        flags.append(RedFlag(
            rule_id="HYP-RF-002",
            description="Diastolischer Blutdruck >= 120 mmHg: Hypertensiver Notfall moeglich.",
            severity="critical",
            triggered_by=f"diastolisch={int(dia_val)}",
        ))

    if _parse_ja_nein(answers.get("brustschmerz", "")):
        flags.append(RedFlag(
            rule_id="HYP-RF-003",
            description="Brustschmerz bei Bluthochdruck: Kardiales Ereignis nicht auszuschliessen.",
            severity="critical",
            triggered_by="brustschmerz=ja",
        ))

    if _parse_ja_nein(answers.get("atemnot", "")):
        flags.append(RedFlag(
            rule_id="HYP-RF-004",
            description="Atemnot bei Bluthochdruck: Kardiopulmonale Dekompensation nicht auszuschliessen.",
            severity="warning",
            triggered_by="atemnot=ja",
        ))

    if _parse_ja_nein(answers.get("neurologische_symptome", "")):
        flags.append(RedFlag(
            rule_id="HYP-RF-005",
            description="Neurologische Symptome bei Bluthochdruck: Zerebrovaskulaeres Ereignis nicht auszuschliessen.",
            severity="critical",
            triggered_by="neurologische_symptome=ja",
        ))

    if _parse_ja_nein(answers.get("sehstoerungen", "")):
        severity = "critical" if (sys_val and sys_val >= 180) else "warning"
        flags.append(RedFlag(
            rule_id="HYP-RF-006",
            description="Sehstoerungen bei Bluthochdruck: Moeglicher Endorganschaden.",
            severity=severity,
            triggered_by="sehstoerungen=ja",
        ))

    if _parse_ja_nein(answers.get("kopfschmerz", "")):
        severity = "critical" if (sys_val and sys_val >= 180) else "warning"
        flags.append(RedFlag(
            rule_id="HYP-RF-007",
            description="Kopfschmerz bei Bluthochdruck: Hypertensive Krise oder zerebrovaskulaeres Ereignis nicht auszuschliessen.",
            severity=severity,
            triggered_by="kopfschmerz=ja",
        ))

    organ_symptome = sum([
        _parse_ja_nein(answers.get("kopfschmerz", "")),
        _parse_ja_nein(answers.get("brustschmerz", "")),
        _parse_ja_nein(answers.get("atemnot", "")),
        _parse_ja_nein(answers.get("neurologische_symptome", "")),
        _parse_ja_nein(answers.get("sehstoerungen", "")),
    ])
    if organ_symptome >= 2 and sys_val and sys_val >= 160:
        flags.append(RedFlag(
            rule_id="HYP-RF-008",
            description="Mehrere Endorgansymptome bei deutlich erhoehtem Blutdruck: Hypertensiver Notfall mit Organschaden wahrscheinlich.",
            severity="critical",
            triggered_by=f"organ_symptome={organ_symptome}+systolisch={int(sys_val)}",
        ))

    if sys_val and 160 <= sys_val < 180:
        flags.append(RedFlag(
            rule_id="HYP-RF-009",
            description="Systolischer Blutdruck 160-179 mmHg: Hypertonie Grad 2, aerztliche Pruefung empfohlen.",
            severity="warning",
            triggered_by=f"systolisch={int(sys_val)}",
        ))

    if dia_val and 100 <= dia_val < 120:
        flags.append(RedFlag(
            rule_id="HYP-RF-010",
            description="Diastolischer Blutdruck 100-119 mmHg: Hypertonie Grad 2, aerztliche Pruefung empfohlen.",
            severity="warning",
            triggered_by=f"diastolisch={int(dia_val)}",
        ))

    vorerkrankungen = answers.get("vorerkrankungen", "").lower()
    relevante = ("herzinfarkt", "schlaganfall", "niereninsuffizienz", "nierenschaden", "herzinsuffizienz", "khk", "koronar")
    if any(kw in vorerkrankungen for kw in relevante):
        severity = "critical" if (sys_val and sys_val >= 160) else "warning"
        flags.append(RedFlag(
            rule_id="HYP-RF-011",
            description="Relevante kardiovaskulaere oder renale Vorerkrankung bei erhoehtem Blutdruck: Endorganschaden-Risiko erhoet.",
            severity=severity,
            triggered_by=f"vorerkrankungen={answers.get('vorerkrankungen', '')}",
        ))

    puls_val = _parse_number(answers.get("puls", ""))
    if puls_val is not None and puls_val >= 120:
        flags.append(RedFlag(
            rule_id="HYP-RF-012",
            description="Tachykardie (Puls >= 120/min) bei Bluthochdruck: Kardiale Dekompensation nicht auszuschliessen.",
            severity="critical",
            triggered_by=f"puls={int(puls_val)}",
        ))
    elif puls_val is not None and puls_val < 50:
        flags.append(RedFlag(
            rule_id="HYP-RF-013",
            description="Bradykardie (Puls < 50/min) bei Bluthochdruck: Erregungsleitungsstoerung nicht auszuschliessen.",
            severity="warning",
            triggered_by=f"puls={int(puls_val)}",
        ))

    return flags


def check_chest_pain(answers: dict[str, str], vitals: dict[str, int | float] | None = None) -> list[RedFlag]:
    flags: list[RedFlag] = []

    if _parse_ja_nein(answers.get("atemnot", "")):
        flags.append(RedFlag(
            rule_id="CP-RF-001",
            description="Atemnot bei Brustschmerz: Kardiopulmonales Ereignis nicht auszuschliessen.",
            severity="critical",
            triggered_by="atemnot=ja",
        ))

    if _parse_ja_nein(answers.get("kaltschweissigkeit", "")):
        flags.append(RedFlag(
            rule_id="CP-RF-002",
            description="Kaltschweissigkeit bei Brustschmerz: Akutes Koronarsyndrom nicht auszuschliessen.",
            severity="critical",
            triggered_by="kaltschweissigkeit=ja",
        ))

    if _parse_ja_nein(answers.get("synkope", "")):
        flags.append(RedFlag(
            rule_id="CP-RF-003",
            description="Synkope bei Brustschmerz: Sofortige aerztliche Uebernahme erforderlich.",
            severity="critical",
            triggered_by="synkope=ja",
        ))

    ausstrahlung = answers.get("ausstrahlung", "").lower()
    if any(kw in ausstrahlung for kw in ("linker arm", "linke arm", "kiefer", "beide arme")):
        flags.append(RedFlag(
            rule_id="CP-RF-004",
            description="Typische Ausstrahlung (Arm/Kiefer): Kardiales Ereignis nicht auszuschliessen.",
            severity="critical",
            triggered_by=f"ausstrahlung={answers.get('ausstrahlung', '')}",
        ))

    schmerzcharakter = answers.get("schmerzcharakter", "").lower()
    if any(kw in schmerzcharakter for kw in ("drueckend", "drückend", "eng", "vernichtend")):
        if _parse_ja_nein(answers.get("belastungsabhaengigkeit", "")):
            flags.append(RedFlag(
                rule_id="CP-RF-005",
                description="Drueckender/enger Brustschmerz bei Belastung: Typische Angina-pectoris-Konstellation.",
                severity="critical",
                triggered_by="schmerzcharakter+belastungsabhaengigkeit",
            ))

    if _parse_ja_nein(answers.get("bekannte_khk", "")):
        flags.append(RedFlag(
            rule_id="CP-RF-006",
            description="Brustschmerz bei bekannter KHK: Aerztliche Pruefung dringend erforderlich.",
            severity="warning",
            triggered_by="bekannte_khk=ja",
        ))

    if _parse_ja_nein(answers.get("ausgepraege_schwaeche", "")):
        flags.append(RedFlag(
            rule_id="CP-RF-007",
            description="Ausgepreagte Schwaeche bei Brustschmerz: Hinweis auf haemodynamische Instabilitaet.",
            severity="warning",
            triggered_by="ausgepraege_schwaeche=ja",
        ))

    if _parse_ja_nein(answers.get("uebelkeit", "")):
        if _parse_ja_nein(answers.get("kaltschweissigkeit", "")):
            flags.append(RedFlag(
                rule_id="CP-RF-008",
                description="Uebelkeit und Kaltschweissigkeit: Vegetative Begleitsymptomatik eines akuten Koronarsyndroms moeglich.",
                severity="critical",
                triggered_by="uebelkeit+kaltschweissigkeit=ja",
            ))

    schmerzcharakter = answers.get("schmerzcharakter", "").lower()
    if any(kw in schmerzcharakter for kw in ("drueckend", "drückend", "eng", "vernichtend")):
        if not _parse_ja_nein(answers.get("ruhe_besserung", "")):
            ruhe_val = answers.get("ruhe_besserung", "").strip().lower()
            if ruhe_val in ("nein", "n", "no"):
                flags.append(RedFlag(
                    rule_id="CP-RF-009",
                    description="Drueckender/enger Brustschmerz ohne Besserung in Ruhe: Instabile Angina oder ACS nicht auszuschliessen.",
                    severity="critical",
                    triggered_by="schmerzcharakter+ruhe_besserung=nein",
                ))

    if _parse_ja_nein(answers.get("alter_ueber_55", "")):
        risikofaktoren = answers.get("kardiovaskulaere_risikofaktoren", "").lower()
        hat_risikofaktoren = any(kw in risikofaktoren for kw in (
            "rauch", "diabet", "bluthochdruck", "hypertonie", "cholesterin", "famili",
        ))
        if hat_risikofaktoren:
            flags.append(RedFlag(
                rule_id="CP-RF-010",
                description="Alter >55 mit kardiovaskulaeren Risikofaktoren bei Brustschmerz: Erhoehte Wahrscheinlichkeit fuer kardiales Ereignis.",
                severity="warning",
                triggered_by="alter_ueber_55+risikofaktoren",
            ))

    if not _parse_ja_nein(answers.get("druckschmerz_thoraxwand", "")):
        druckschmerz_val = answers.get("druckschmerz_thoraxwand", "").strip().lower()
        if druckschmerz_val in ("nein", "n", "no"):
            if _parse_ja_nein(answers.get("belastungsabhaengigkeit", "")):
                flags.append(RedFlag(
                    rule_id="CP-RF-011",
                    description="Nicht reproduzierbarer Schmerz bei Belastungsabhaengigkeit: Kardiale Genese wahrscheinlicher.",
                    severity="warning",
                    triggered_by="druckschmerz_thoraxwand=nein+belastungsabhaengigkeit=ja",
                ))

    sys_val = vitals.get("systolisch") if vitals else None
    dia_val = vitals.get("diastolisch") if vitals else None

    if sys_val is not None and sys_val >= 180:
        flags.append(RedFlag(
            rule_id="CP-RF-012",
            description="Systolischer Blutdruck >= 180 mmHg bei Brustschmerz: Hypertensiver Notfall mit kardialem Risiko.",
            severity="critical",
            triggered_by=f"systolisch={int(sys_val)}",
        ))

    if dia_val is not None and dia_val >= 120:
        flags.append(RedFlag(
            rule_id="CP-RF-013",
            description="Diastolischer Blutdruck >= 120 mmHg bei Brustschmerz: Hypertensiver Notfall mit kardialem Risiko.",
            severity="critical",
            triggered_by=f"diastolisch={int(dia_val)}",
        ))

    spo2 = vitals.get("spo2") if vitals else None
    if spo2 is not None and spo2 < 92:
        flags.append(RedFlag(
            rule_id="CP-RF-014",
            description="SpO2 < 92% bei Brustschmerz: Relevante Hypoxaemie, sofortige aerztliche Uebernahme erforderlich.",
            severity="critical",
            triggered_by=f"spo2={spo2}",
        ))

    return flags


def check_diabetes(answers: dict[str, str], vitals: dict[str, int | float] | None = None) -> list[RedFlag]:
    flags: list[RedFlag] = []

    symptom_text = answers.get("hypo_hyper_beschwerden", "").lower()
    wunde_text = answers.get("offene_wunde_fussproblem_details", "").lower()
    blutzucker_text = answers.get("blutzuckerwert_details", "")

    systolisch = _parse_number(answers.get("blutdruck_systolisch", ""))
    diastolisch = _parse_number(answers.get("blutdruck_diastolisch", ""))

    if vitals:
        systolisch = systolisch or vitals.get("systolisch")
        diastolisch = diastolisch or vitals.get("diastolisch")

    if _parse_ja_nein(answers.get("hypo_hyper_hinweise", "")):
        flags.append(RedFlag(
            rule_id="DM-RF-001",
            description="Hinweise auf Hypo- oder Hyperglykaemie: Aerztliche Pruefung empfohlen.",
            severity="warning",
            triggered_by="hypo_hyper_hinweise=ja",
        ))

    if any(keyword in symptom_text for keyword in ("bewusst", "verwirrt", "verwirrtheit", "ohnmacht")):
        flags.append(RedFlag(
            rule_id="DM-RF-002",
            description="Bewusstseinsstoerung oder Verwirrtheit bei Diabetes: Schwere Stoffwechselentgleisung nicht auszuschliessen.",
            severity="critical",
            triggered_by=f"hypo_hyper_beschwerden={answers.get('hypo_hyper_beschwerden', '')}",
        ))

    if any(keyword in symptom_text for keyword in ("erbrechen", "atemnot", "luftnot", "dehyd")):
        flags.append(RedFlag(
            rule_id="DM-RF-003",
            description="Erbrechen, Atemnot oder Dehydratation bei Diabetes: Akute Stoffwechselentgleisung nicht auszuschliessen.",
            severity="critical",
            triggered_by=f"hypo_hyper_beschwerden={answers.get('hypo_hyper_beschwerden', '')}",
        ))

    if any(keyword in symptom_text for keyword in ("brustschmerz", "druck auf der brust", "druckgefuehl")):
        flags.append(RedFlag(
            rule_id="DM-RF-004",
            description="Brustschmerz im Diabetes-Szenario: Sofortige aerztliche Abklaerung erforderlich.",
            severity="critical",
            triggered_by=f"hypo_hyper_beschwerden={answers.get('hypo_hyper_beschwerden', '')}",
        ))

    if any(keyword in symptom_text for keyword in ("sehstoer", "verschwommen")):
        flags.append(RedFlag(
            rule_id="DM-RF-005",
            description="Sehstoerungen bei Diabetes: Aerztliche Pruefung empfohlen.",
            severity="warning",
            triggered_by=f"hypo_hyper_beschwerden={answers.get('hypo_hyper_beschwerden', '')}",
        ))

    if _parse_ja_nein(answers.get("offene_wunde_fussproblem", "")):
        severity = "critical" if any(keyword in wunde_text for keyword in ("verschlechter", "entzu", "sekret", "stark")) else "warning"
        flags.append(RedFlag(
            rule_id="DM-RF-006",
            description="Fussproblem oder offene Wunde bei Diabetes: Diabetischer Fuss oder Infektion muss aerztlich beurteilt werden.",
            severity=severity,
            triggered_by="offene_wunde_fussproblem=ja",
        ))

    blutzuckerwert = _extract_first_number(blutzucker_text)
    if blutzuckerwert is not None and blutzuckerwert < 70:
        flags.append(RedFlag(
            rule_id="DM-RF-007",
            description="Sehr niedriger angegebener Blutzuckerwert (< 70 mg/dl): Hypoglykaemie moeglich.",
            severity="critical",
            triggered_by=f"blutzuckerwert={blutzuckerwert}",
        ))
    elif blutzuckerwert is not None and blutzuckerwert >= 300:
        flags.append(RedFlag(
            rule_id="DM-RF-008",
            description="Sehr hoher angegebener Blutzuckerwert (>= 300 mg/dl): Hyperglykaemie moeglich.",
            severity="critical",
            triggered_by=f"blutzuckerwert={blutzuckerwert}",
        ))

    if systolisch is not None and systolisch >= 180:
        flags.append(RedFlag(
            rule_id="DM-RF-009",
            description="Systolischer Blutdruck >= 180 mmHg im Diabetes-Szenario: Kritischer Blutdruckwert.",
            severity="critical",
            triggered_by=f"systolisch={int(systolisch)}",
        ))

    if diastolisch is not None and diastolisch >= 120:
        flags.append(RedFlag(
            rule_id="DM-RF-010",
            description="Diastolischer Blutdruck >= 120 mmHg im Diabetes-Szenario: Kritischer Blutdruckwert.",
            severity="critical",
            triggered_by=f"diastolisch={int(diastolisch)}",
        ))

    hba1c_text = answers.get("hba1c_wert", "")
    hba1c_val = _extract_first_number(hba1c_text)
    if hba1c_val is not None and hba1c_val >= 10:
        flags.append(RedFlag(
            rule_id="DM-RF-011",
            description="HbA1c >= 10%: Stark unzureichende Stoffwechseleinstellung, aerztliche Pruefung dringend empfohlen.",
            severity="critical",
            triggered_by=f"hba1c={hba1c_val}",
        ))
    elif hba1c_val is not None and hba1c_val >= 8.5:
        flags.append(RedFlag(
            rule_id="DM-RF-012",
            description="HbA1c >= 8.5%: Unzureichende Stoffwechseleinstellung, aerztliche Pruefung empfohlen.",
            severity="warning",
            triggered_by=f"hba1c={hba1c_val}",
        ))

    gewichtsveraenderung_details = answers.get("gewichtsveraenderung_details", "").lower()
    if _parse_ja_nein(answers.get("gewichtsveraenderung", "")):
        if any(kw in gewichtsveraenderung_details for kw in ("abgenommen", "abnahme", "verlust", "verloren", "weniger")):
            abnahme_wert = _extract_first_number(gewichtsveraenderung_details)
            if abnahme_wert is not None and abnahme_wert >= 5:
                flags.append(RedFlag(
                    rule_id="DM-RF-013",
                    description="Signifikanter Gewichtsverlust (>= 5 kg) bei Diabetes: Moeglicher Hinweis auf unkontrollierten Diabetes oder Begleiterkrankung.",
                    severity="warning",
                    triggered_by=f"gewichtsveraenderung_details={answers.get('gewichtsveraenderung_details', '')}",
                ))

    if _parse_ja_nein(answers.get("folgeerkrankungen_bekannt", "")):
        folge_details = answers.get("folgeerkrankungen_details", "").lower()
        if _parse_ja_nein(answers.get("hypo_hyper_hinweise", "")):
            flags.append(RedFlag(
                rule_id="DM-RF-014",
                description="Bekannte Folgeerkrankungen bei gleichzeitigen Hypo-/Hyperglykämie-Hinweisen: Erhoehtes Risiko fuer Komplikationen.",
                severity="critical",
                triggered_by="folgeerkrankungen+hypo_hyper_hinweise",
            ))
        if any(kw in folge_details for kw in ("nephro", "niere", "dialyse")):
            flags.append(RedFlag(
                rule_id="DM-RF-015",
                description="Diabetische Nephropathie bekannt: Blutdruck und Nierenfunktion aerztlich kontrollieren.",
                severity="warning",
                triggered_by=f"folgeerkrankungen_details={answers.get('folgeerkrankungen_details', '')}",
            ))

    medikamente = answers.get("medikamente", "").lower()
    if any(kw in medikamente for kw in ("insulin", "sulfonylharnstoff", "glibenclamid", "glimepirid")):
        if _parse_ja_nein(answers.get("hypo_hyper_hinweise", "")):
            if any(kw in symptom_text for kw in ("zitter", "schweiss", "schwindel", "schwach")):
                flags.append(RedFlag(
                    rule_id="DM-RF-016",
                    description="Hypoglykaemie-Symptome bei Insulin-/Sulfonylharnstoff-Therapie: Erhoehtes Risiko fuer schwere Unterzuckerung.",
                    severity="critical",
                    triggered_by="medikamente+hypo_symptome",
                ))

    return flags


def check_cough(answers: dict[str, str], vitals: dict[str, int | float] | None = None) -> list[RedFlag]:
    flags: list[RedFlag] = []

    if _parse_ja_nein(answers.get("dyspnoe", "")):
        flags.append(RedFlag(
            rule_id="COUGH-RF-001",
            description="Atemnot bei akutem Husten: Pneumonie oder kardiopulmonale Ursache nicht auszuschliessen.",
            severity="critical",
            triggered_by="dyspnoe=ja",
        ))

    if _parse_ja_nein(answers.get("blutbeimengung", "")):
        flags.append(RedFlag(
            rule_id="COUGH-RF-002",
            description="Haemoptysen (Blut im Auswurf): Sofortige aerztliche Abklaerung erforderlich.",
            severity="critical",
            triggered_by="blutbeimengung=ja",
        ))

    if _parse_ja_nein(answers.get("fieber", "")):
        severity = "warning"
        if _parse_ja_nein(answers.get("dyspnoe", "")) or _parse_ja_nein(answers.get("thorakale_schmerzen", "")):
            severity = "critical"
        flags.append(RedFlag(
            rule_id="COUGH-RF-003",
            description="Fieber oder Schuettelfrost bei akutem Husten: Infektioeses Geschehen, Pneumonie nicht auszuschliessen.",
            severity=severity,
            triggered_by="fieber=ja",
        ))

    if _parse_ja_nein(answers.get("thorakale_schmerzen", "")):
        flags.append(RedFlag(
            rule_id="COUGH-RF-004",
            description="Thorakale Schmerzen bei akutem Husten: Pleuritis oder kardiopulmonale Ursache nicht auszuschliessen.",
            severity="warning",
            triggered_by="thorakale_schmerzen=ja",
        ))

    vorerkrankungen = answers.get("vorerkrankungen", "").lower()
    relevante = ("copd", "asthma", "herzinsuffizienz", "immunsuppression", "immunschwaeche", "krebs", "tumor", "transplant")
    if any(kw in vorerkrankungen for kw in relevante):
        severity = "critical" if _parse_ja_nein(answers.get("fieber", "")) else "warning"
        flags.append(RedFlag(
            rule_id="COUGH-RF-005",
            description="Relevante Vorerkrankung bei akutem Husten: Erhoehtes Komplikationsrisiko, aerztliche Pruefung erforderlich.",
            severity=severity,
            triggered_by=f"vorerkrankungen={answers.get('vorerkrankungen', '')}",
        ))

    if _parse_ja_nein(answers.get("belastungsdyspnoe", "")) and not _parse_ja_nein(answers.get("dyspnoe", "")):
        flags.append(RedFlag(
            rule_id="COUGH-RF-006",
            description="Belastungsdyspnoe bei akutem Husten: Respiratorische Einschraenkung moeglich.",
            severity="warning",
            triggered_by="belastungsdyspnoe=ja",
        ))

    spo2 = vitals.get("spo2") if vitals else None
    if spo2 is not None and spo2 < 92:
        flags.append(RedFlag(
            rule_id="COUGH-RF-007",
            description="SpO2 < 92%: Relevante Hypoxaemie, sofortige aerztliche Uebernahme erforderlich.",
            severity="critical",
            triggered_by=f"spo2={spo2}",
        ))
    elif spo2 is not None and spo2 < 95:
        flags.append(RedFlag(
            rule_id="COUGH-RF-008",
            description="SpO2 zwischen 92-94%: Leichte Hypoxaemie, aerztliche Pruefung empfohlen.",
            severity="warning",
            triggered_by=f"spo2={spo2}",
        ))

    auswurf = answers.get("auswurf_farbe", "").lower()
    if any(kw in auswurf for kw in ("blutig", "blut", "rosafarben", "rostfarben")):
        if not _parse_ja_nein(answers.get("blutbeimengung", "")):
            flags.append(RedFlag(
                rule_id="COUGH-RF-009",
                description="Blutiger oder rostfarbener Auswurf: Haemoptysen moeglich, aerztliche Abklaerung erforderlich.",
                severity="critical",
                triggered_by=f"auswurf_farbe={answers.get('auswurf_farbe', '')}",
            ))

    return flags


def _extract_first_number(value: str) -> float | None:
    tokens = value.replace(",", ".").split()
    for token in tokens:
        number = _parse_number(token)
        if number is not None:
            return number
    return None


def check(scenario: str, answers: dict[str, str], vitals: dict | None = None) -> list[RedFlag]:
    if scenario == "cough":
        return check_cough(answers, vitals)
    if scenario == "hypertension":
        return check_hypertension(answers, vitals)
    if scenario == "chest_pain":
        return check_chest_pain(answers, vitals)
    if scenario == "diabetes":
        return check_diabetes(answers, vitals)
    return []
