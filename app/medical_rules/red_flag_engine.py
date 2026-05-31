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

    return flags


def _extract_first_number(value: str) -> float | None:
    tokens = value.replace(",", ".").split()
    for token in tokens:
        number = _parse_number(token)
        if number is not None:
            return number
    return None


def check(scenario: str, answers: dict[str, str], vitals: dict | None = None) -> list[RedFlag]:
    if scenario == "hypertension":
        return check_hypertension(answers, vitals)
    if scenario == "chest_pain":
        return check_chest_pain(answers, vitals)
    if scenario == "diabetes":
        return check_diabetes(answers, vitals)
    return []
