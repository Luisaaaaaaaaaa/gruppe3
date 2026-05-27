import tkinter as tk
from tkinter import ttk

from app.identity.identity_check import AuthenticationResult


class LoginForm(ttk.Frame):
    def __init__(self, master: tk.Misc, on_submit, max_attempts: int) -> None:
        super().__init__(master, padding=24)
        self._on_submit = on_submit
        self._build_widgets(max_attempts)

    def _build_widgets(self, max_attempts: int) -> None:
        self.columnconfigure(0, weight=1)

        title = ttk.Label(self, text="Patientenanmeldung", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            self,
            text=(
                "Bitte melden Sie sich mit Ihrem Vornamen, Nachnamen und Geburtsdatum an. "
                "Dieses System ist ausschließlich ein Assistenzsystem und stellt keine Diagnosen "
                "und keine Therapieempfehlungen."
            ),
            wraplength=560,
            justify="left",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(10, 18))

        self.status_var = tk.StringVar(
            value=f"Zur Verfuegung stehende Anmeldeversuche: {max_attempts}"
        )
        status_label = ttk.Label(self, textvariable=self.status_var, foreground="#1f4e79")
        status_label.grid(row=2, column=0, sticky="w", pady=(0, 16))

        form = ttk.Frame(self)
        form.grid(row=3, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Vorname").grid(row=0, column=0, sticky="w", pady=6)
        self.first_name_entry = ttk.Entry(form)
        self.first_name_entry.grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(form, text="Nachname").grid(row=1, column=0, sticky="w", pady=6)
        self.last_name_entry = ttk.Entry(form)
        self.last_name_entry.grid(row=1, column=1, sticky="ew", pady=6)

        birthday_wrapper = ttk.Frame(form)
        birthday_wrapper.grid(row=2, column=1, sticky="w", pady=6)
        ttk.Label(form, text="Geburtsdatum").grid(row=2, column=0, sticky="w", pady=6)

        self.day_entry = ttk.Entry(birthday_wrapper, width=5)
        self.day_entry.grid(row=0, column=0, padx=(0, 8))
        ttk.Label(birthday_wrapper, text=".").grid(row=0, column=1)
        self.month_entry = ttk.Entry(birthday_wrapper, width=5)
        self.month_entry.grid(row=0, column=2, padx=8)
        ttk.Label(birthday_wrapper, text=".").grid(row=0, column=3)
        self.year_entry = ttk.Entry(birthday_wrapper, width=7)
        self.year_entry.grid(row=0, column=4, padx=(8, 0))

        ttk.Label(birthday_wrapper, text="TT").grid(row=1, column=0)
        ttk.Label(birthday_wrapper, text="MM").grid(row=1, column=2)
        ttk.Label(birthday_wrapper, text="JJJJ").grid(row=1, column=4)

        self.message_var = tk.StringVar(value="")
        self.message_label = ttk.Label(
            self,
            textvariable=self.message_var,
            wraplength=560,
            justify="left",
        )
        self.message_label.grid(row=4, column=0, sticky="w", pady=(18, 18))

        button_frame = ttk.Frame(self)
        button_frame.grid(row=5, column=0, sticky="e")
        button_frame.columnconfigure(0, weight=1)

        cancel_button = ttk.Button(button_frame, text="Abbrechen", command=self._cancel)
        cancel_button.grid(row=0, column=0, padx=(0, 8))

        self.submit_button = ttk.Button(button_frame, text="Anmelden", command=self._submit)
        self.submit_button.grid(row=0, column=1)

        self.first_name_entry.focus_set()

    def _cancel(self) -> None:
        self.master.destroy()

    def _submit(self) -> None:
        self._on_submit(
            self.first_name_entry.get(),
            self.last_name_entry.get(),
            self.day_entry.get(),
            self.month_entry.get(),
            self.year_entry.get(),
        )

    def show_result(self, result: AuthenticationResult) -> None:
        self.message_var.set(result.message)
        color = "#0f5132" if result.success else "#8a1c1c"
        self.message_label.configure(foreground=color)
        self.status_var.set(
            "Anmeldung erfolgreich."
            if result.success
            else f"Verbleibende Anmeldeversuche: {result.attempts_left}"
        )

        if result.success or result.escalate:
            self.submit_button.configure(state="disabled")
            self._disable_entries()

    def _disable_entries(self) -> None:
        self.first_name_entry.configure(state="disabled")
        self.last_name_entry.configure(state="disabled")
        self.day_entry.configure(state="disabled")
        self.month_entry.configure(state="disabled")
        self.year_entry.configure(state="disabled")
