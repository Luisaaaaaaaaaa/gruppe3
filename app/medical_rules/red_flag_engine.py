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


def check(scenario: str, answers: dict[str, str], vitals: dict | None = None) -> list[RedFlag]:
    if scenario == "hypertension":
        return check_hypertension(answers, vitals)
    if scenario == "chest_pain":
        return check_chest_pain(answers, vitals)
    return []
