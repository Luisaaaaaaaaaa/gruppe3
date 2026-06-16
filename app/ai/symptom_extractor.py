from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scenarios.hypertension_scenario import AnamnesisQuestion


def _load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


def extract_answers(
    patient_text: str,
    questions: list[AnamnesisQuestion],
) -> dict[str, str]:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or not patient_text.strip():
        return {}

    try:
        import google.generativeai as genai
    except ImportError:
        return {}

    genai.configure(api_key=api_key)

    questions_desc = []
    for q in questions:
        entry = {"key": q.key, "text": q.text, "type": q.input_type}
        questions_desc.append(entry)

    questions_json = json.dumps(questions_desc, ensure_ascii=False, indent=2)

    prompt = (
        "Du bist ein medizinischer Assistent in einer Hausarztpraxis. "
        "Ein Patient hat folgende Beschwerden geschildert:\n\n"
        f'"{patient_text}"\n\n'
        "Extrahiere aus dem Text Antworten auf die folgenden Fragen. "
        "Antworte ausschliesslich im JSON-Format als ein Objekt mit den "
        "Frage-Keys als Schluessel und den Antworten als Werte.\n\n"
        "Regeln:\n"
        '- Fuer ja_nein-Fragen antworte mit "Ja" oder "Nein".\n'
        "- Fuer freitext-Fragen gib die relevante Information aus dem Text "
        "in knappen Worten wieder.\n"
        "- Fuer zahl-Fragen gib nur die Zahl als String an.\n"
        "- Wenn eine Frage NICHT aus dem Text beantwortet werden kann, "
        'setze den Wert auf "" (leerer String).\n'
        "- Erfinde keine Informationen, die nicht im Text stehen.\n\n"
        f"Fragen:\n{questions_json}\n\n"
        "Antwort (nur JSON, kein weiterer Text):"
    )

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            lines = raw.splitlines()
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines)

        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}

        valid_keys = {q.key for q in questions}
        return {k: str(v) for k, v in parsed.items() if k in valid_keys and v}

    except Exception:
        return {}
