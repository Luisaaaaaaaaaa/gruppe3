ROLE_EXPLANATION = (
    "Herzlich Willkommen. Dieses System ist ein digitales, KI-gestütztes Assistenzsystem zur "
    "strukturierten Erhebung von Gesundheitsinformationen.\n\n"
    "Wichtige Hinweise:\n"
    "- Das System stellt keine Diagnosen.\n"
    "- Das System gibt keine Therapieempfehlungen.\n"
    "- Das System ersetzt keine ärztliche Beratung.\n"
    "- Die abschließende medizinische Bewertung erfolgt ausschließlich "
    "durch ärztliches Personal.\n\n"
    "Ihre Angaben werden strukturiert erfasst und dem ärztlichen Personal "
    "als Zusammenfassung übergeben."
)

CONSENT_QUESTION = (
    "Möchten Sie mit der assistierten Anamnese fortfahren?\n"
)

CONSENT_DECLINED = (
    "Sie haben die assistierte Anamnese abgelehnt. "
    "Bitte wenden Sie sich an das Praxispersonal."
)

CONSENT_ACCEPTED = (
    "Vielen Dank. Die assistierte Anamnese beginnt nun. "
    "Sie können jederzeit 'Abbrechen' eingeben oder auf den Abbrechen-Button klicken, um die Anamnese zu beenden."
)


def is_consent_given(answer: str) -> bool | None:
    normalized = answer.strip().lower()
    if normalized in ("ja", "j", "yes", "y"):
        return True
    if normalized in ("nein", "n", "no"):
        return False
    return None
