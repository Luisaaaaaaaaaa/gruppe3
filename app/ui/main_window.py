from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from app.identity.identity_check import IdentityCheck
from app.patient_import.patient_list_client import PatientListClient
from app.ui.form_frame import LoginForm


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SET Patientenanmeldung")
        self.root.geometry("680x420")
        self.root.minsize(640, 400)

        style = ttk.Style()
        style.theme_use("clam")

        repository = PatientListClient(
            Path("app/patient_import/patientenTagesliste.json")
        )
        patients = repository.load_patients()
        self.identity_check = IdentityCheck(patients=patients, max_attempts=3)

        self.form = LoginForm(
            root,
            on_submit=self.handle_submit,
            max_attempts=self.identity_check.max_attempts,
        )
        self.form.pack(fill="both", expand=True)

    def handle_submit(
        self, first_name: str, last_name: str, day: str, month: str, year: str
    ) -> None:
        if not first_name.strip() or not last_name.strip():
            self.form.message_var.set("Vorname und Nachname muessen ausgefuellt werden.")
            self.form.message_label.configure(foreground="#8a1c1c")
            return

        if not (day.isdigit() and month.isdigit() and year.isdigit()):
            self.form.message_var.set(
                "Bitte geben Sie das Geburtsdatum als Zahlen in TT.MM.JJJJ ein."
            )
            self.form.message_label.configure(foreground="#8a1c1c")
            return

        if len(year) != 4:
            self.form.message_var.set("Das Jahr muss vierstellig eingegeben werden.")
            self.form.message_label.configure(foreground="#8a1c1c")
            return

        try:
            parsed_birth_date = date(int(year), int(month), int(day))
        except ValueError:
            self.form.message_var.set("Bitte geben Sie ein gueltiges Kalenderdatum ein.")
            self.form.message_label.configure(foreground="#8a1c1c")
            return

        date_of_birth = parsed_birth_date.isoformat()
        result = self.identity_check.authenticate(
            first_name, last_name, date_of_birth
        )
        self.form.show_result(result)


def run_app() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()
