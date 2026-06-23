import re


def normalize_person_name(value: str) -> str:
    """Normalisiert Namen fuer Eingabe, Speicherung und Vergleich."""
    collapsed = re.sub(r"\s+", " ", value.strip())
    return re.sub(r"\s*-\s*", "-", collapsed)


def person_name_key(value: str) -> str:
    return normalize_person_name(value).casefold()
