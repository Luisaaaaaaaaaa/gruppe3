from app.patient_import.patient_schema import PatientRecord

# Priorität: diabetes > hypertension > chest_pain > cough
_SCENARIO_MAP: list[tuple[str, list[str]]] = [
    ("diabetes", ["diabetes", "e11", "e10", "e14", "typ-2-diabetes", "typ 2 diabetes"]),
    ("hypertension", ["hypertonie", "hypertonus", "i10", "i11", "i12", "i13", "i15", "bluthochdruck"]),
    ("chest_pain", ["herzkrankheit", "koronar", "kardial", "vorhofflimmern", "i25", "i48", "i49", "i20", "i21", "i50", "angina"]),
    ("cough", ["copd", "asthma", "j44", "j45", "j43", "immunsuppression", "herzinsuffizienz", "i50", "bronchitis"]),
]


def recommend_scenario(patient: PatientRecord) -> str | None:
    """Analysiert die Vorerkrankungen eines Patienten und empfiehlt ein Szenario.

    Args:
        patient: Der Patient mit conditions-String und medications-Liste.

    Returns:
        Scenario-Key ("cough", "chest_pain", "hypertension", "diabetes")
        oder None, wenn keine passende Vorerkrankung gefunden wurde.
    """
    if not patient.conditions:
        return None

    conditions_lower = patient.conditions.lower()

    for scenario_key, keywords in _SCENARIO_MAP:
        for keyword in keywords:
            if keyword in conditions_lower:
                return scenario_key

    return None
