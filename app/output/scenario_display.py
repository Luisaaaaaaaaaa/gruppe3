SCENARIO_TITLES: dict[str, tuple[str, str]] = {
    "A": ("A", "Akuter Husten"),
    "cough": ("A", "Akuter Husten"),
    "B": ("B", "Brustschmerz"),
    "chest_pain": ("B", "Brustschmerz"),
    "C": ("C", "Hypertonie-Kontrolle"),
    "hypertension": ("C", "Hypertonie-Kontrolle"),
    "D": ("D", "Typ-2-Diabetes"),
    "diabetes": ("D", "Typ-2-Diabetes"),
}


def get_scenario_title(scenario_key: str) -> str:
    key = str(scenario_key or "").strip()
    scenario = SCENARIO_TITLES.get(key)
    if scenario is None:
        return key
    ui_key, title = scenario
    return f"Szenario {ui_key} - {title}"
