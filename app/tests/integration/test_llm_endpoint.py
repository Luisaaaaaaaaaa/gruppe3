"""Eigenstaendiger Verbindungstest fuer den OpenAI-kompatiblen LLM-Endpunkt.

Ruft denselben Server/dasselbe Modell auf, das auch der Symptom-Extractor
verwendet. Konfiguration ueber .env (LLM_BASE_URL / LLM_API_KEY / LLM_MODEL)
oder die Standardwerte unten.

Ausfuehren:  python -m app.tests.integration.test_llm_endpoint
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_BASE_URL = "http://141.19.87.240:8000/v1"
DEFAULT_API_KEY = "local-dev-key"
DEFAULT_MODEL = "deepseek-v4-pro"


def _load_env() -> None:
    for parent in Path(__file__).resolve().parents:
        env_path = parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
            break


def main() -> None:
    _load_env()
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", DEFAULT_API_KEY)
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    print(f"Endpunkt: {base_url}")
    print(f"Modell:   {model}\n")

    try:
        from openai import OpenAI
    except ImportError:
        print("FEHLER: openai-Bibliothek nicht installiert (pip install openai).")
        return

    client = OpenAI(base_url=base_url, api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Antworte nur mit dem Wort: OK"}],
            temperature=0.0,
            max_tokens=50,
        )
        text = response.choices[0].message.content
        print("ERFOLG: Die API antwortet.")
        print("Antwort:", (text or "").strip())
    except Exception as exc:  # noqa: BLE001
        print(f"FEHLER: {type(exc).__name__}: {exc}")
        print(">> Pruefe, ob der Server erreichbar ist und das Modell geladen wurde.")


if __name__ == "__main__":
    main()
