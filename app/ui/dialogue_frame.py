import tkinter as tk
from tkinter import ttk
from typing import Callable


class DialogueFrame(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self._input_callback: Callable[[str], None] | None = None
        self._build_widgets()

    def _build_widgets(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        title = ttk.Label(
            self, text="Assistierte Anamnese", font=("Segoe UI", 16, "bold")
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        chat_frame = ttk.Frame(self)
        chat_frame.grid(row=1, column=0, sticky="nsew")
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self._chat_text = tk.Text(
            chat_frame,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 11),
            bg="#f8f9fa",
            relief="flat",
            padx=10,
            pady=10,
        )
        self._chat_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(chat_frame, command=self._chat_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._chat_text.configure(yscrollcommand=scrollbar.set)

        self._chat_text.tag_configure("system", foreground="#1f4e79")
        self._chat_text.tag_configure("user", foreground="#2d5016")
        self._chat_text.tag_configure("warning", foreground="#8a1c1c", font=("Segoe UI", 11, "bold"))

        input_frame = ttk.Frame(self)
        input_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        input_frame.columnconfigure(0, weight=1)

        self._input_entry = ttk.Entry(input_frame, font=("Segoe UI", 11))
        self._input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._input_entry.bind("<Return>", self._on_submit)

        self._send_button = ttk.Button(
            input_frame, text="Senden", command=self._on_submit
        )
        self._send_button.grid(row=0, column=1)

        self._cancel_button = ttk.Button(
            input_frame, text="Abbrechen", command=self._on_cancel
        )
        self._cancel_button.grid(row=0, column=2, padx=(8, 0))

        self._set_input_enabled(False)

    def display_message(self, text: str) -> None:
        tag = "system"
        if "ESKALATION" in text or "ACHTUNG" in text or "WARNHINWEIS" in text:
            tag = "warning"

        self._chat_text.configure(state="normal")
        self._chat_text.insert("end", f"{text}\n", tag)
        self._chat_text.configure(state="disabled")
        self._chat_text.see("end")

    def request_input(self, callback: Callable[[str], None]) -> None:
        self._input_callback = callback
        self._set_input_enabled(True)
        self._input_entry.focus_set()

    def _on_submit(self, _event=None) -> None:
        text = self._input_entry.get().strip()
        if not text:
            return

        self._chat_text.configure(state="normal")
        self._chat_text.insert("end", f"> {text}\n", "user")
        self._chat_text.configure(state="disabled")
        self._chat_text.see("end")

        self._input_entry.delete(0, "end")
        self._set_input_enabled(False)

        if self._input_callback:
            callback = self._input_callback
            self._input_callback = None
            self.after(50, lambda: callback(text))

    def _on_cancel(self) -> None:
        if self._input_callback:
            callback = self._input_callback
            self._input_callback = None
            self._set_input_enabled(False)
            self.after(50, lambda: callback("abbrechen"))

    def _set_input_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._input_entry.configure(state=state)
        self._send_button.configure(state=state)
