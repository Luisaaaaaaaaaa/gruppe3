import tkinter as tk
from tkinter import ttk
from typing import Callable

from app.patient_import.patient_schema import PatientRecord


class ScenarioSelectionFrame(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        patient: PatientRecord,
        on_scenario_selected: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, padding=24)
        self._on_scenario_selected = on_scenario_selected
        self._build_widgets(patient)

    def _build_widgets(self, patient: PatientRecord) -> None:
        self.columnconfigure(0, weight=1)

        title = ttk.Label(self, text="Szenario auswählen", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        patient_info = ttk.Label(
            self, text=f"Angemeldet: {patient.first_name} {patient.last_name}"
        )
        patient_info.grid(row=1, column=0, sticky="w", pady=(10, 18))

        scenarios = [
            ("A", "Szenario A: Akuter Husten / Atemwegsinfekt"),
            ("B", "Szenario B: Brustschmerz"),
            ("C", "Szenario C: Hypertonie-Kontrolle"),
            ("D", "Szenario D: Typ-2-Diabetes"),
        ]

        for i, (key, text) in enumerate(scenarios):
            btn = ttk.Button(
                self, text=text,
                command=lambda k=key: self._on_select(k)
            )
            btn.grid(row=2 + i, column=0, sticky="ew", pady=(0, 6) if i < 3 else (0, 0))

        self.selection_label = ttk.Label(self, text="", wraplength=560)
        self.selection_label.grid(row=6, column=0, sticky="w", pady=(18, 0))

    def _on_select(self, scenario_key: str) -> None:
        if self._on_scenario_selected:
            self._on_scenario_selected(scenario_key)
        else:
            self.selection_label.config(text=f"Szenario {scenario_key} wurde ausgewählt.")
