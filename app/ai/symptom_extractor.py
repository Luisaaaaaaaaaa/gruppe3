from __future__ import annotations

import json
from app.logger.audit_logger import log_info
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scenarios.hypertension_scenario import AnamnesisQuestion


# Konfiguration des LLM-Endpunkts. Standardwerte zeigen auf den
# selbst-gehosteten, OpenAI-kompatiblen Server. Per .env überschreibbar:
#   LLM_BASE_URL=...
#   LLM_API_KEY=...
#   LLM_MODEL=...
_DEFAULT_BASE_URL = "http://141.19.87.240:8000/v1"
_DEFAULT_API_KEY = "local-dev-key"
_DEFAULT_MODEL = "deepseek-v4-pro"

# Zeitlimit (Sekunden) pro LLM-Aufruf. Ist der Server nicht erreichbar oder
# antwortet er nicht, schlaegt der Aufruf nach dieser Zeit fehl, statt die
# Oberflaeche blockieren zu lassen. Per .env ueberschreibbar: LLM_TIMEOUT.
_DEFAULT_TIMEOUT_SECONDS = 15.0


def _request_timeout_seconds() -> float:
    try:
        return float(os.environ.get("LLM_TIMEOUT", _DEFAULT_TIMEOUT_SECONDS))
    except (TypeError, ValueError):
        return _DEFAULT_TIMEOUT_SECONDS


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
    if not patient_text.strip():
        log_info("Kein Patiententext vorhanden, überspringe KI-Antwort-Extraktion.")
        return {}

    base_url = os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", _DEFAULT_API_KEY)
    model = os.environ.get("LLM_MODEL", _DEFAULT_MODEL)

    try:
        from openai import APIConnectionError, APITimeoutError, OpenAI

        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=_request_timeout_seconds(),
            max_retries=0,
        )
    except ImportError:
        log_info(
            "openai-Bibliothek nicht installiert (pip install openai), "
            "überspringe KI-Antwort-Extraktion."
        )
        return {"_error": "KI-Agent ist derzeit nicht verfügbar (openai nicht installiert)."}
    except Exception as exc:
        log_info(
            "Fehler beim Erstellen des KI-Clients: "
            f"{type(exc).__name__}: {exc}"
        )
        return {"_error": "KI-Agent ist derzeit nicht verfügbar."}

    questions_desc = [
        {
            "key": q.key,
            "text": q.text,
            "type": q.input_type,
        }
        for q in questions
    ]

    questions_json = json.dumps(
        questions_desc,
        ensure_ascii=False,
        indent=2,
    )

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

    raw = ""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein praeziser Extraktions-Assistent. "
                        "Du antwortest ausschliesslich mit gueltigem JSON, "
                        "ohne erklaerenden Text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        raw = response.choices[0].message.content
        if not raw:
            log_info(
                "KI-Antwort enthielt keinen Text. "
                f"Vollständige Antwort: {response!r}"
            )
            return {}

        raw = raw.strip()

        if raw.startswith("```"):
            lines = raw.splitlines()
            lines = [
                line
                for line in lines
                if not line.strip().startswith("```")
            ]
            raw = "\n".join(lines)

        parsed = json.loads(raw)

        if not isinstance(parsed, dict):
            log_info(
                f"KI-Antwort war kein JSON-Objekt, sondern {type(parsed).__name__}: {raw!r}"
            )
            return {}

        valid_keys = {q.key for q in questions}

        result = {
            k: str(v)
            for k, v in parsed.items()
            if k in valid_keys and v
        }

        if not result:
            # JSON kam an, aber nichts Verwertbares (unbekannte Keys oder
            # nur leere Werte). Hilft bei der Fehlersuche.
            log_info(
                "KI lieferte keine verwertbaren Antworten. "
                f"Erlaubte Keys: {sorted(valid_keys)} – "
                f"Antwort-Keys: {sorted(parsed.keys())}"
            )

        return result

    except (APIConnectionError, APITimeoutError) as exc:
        log_info(
            "KI-Server nicht erreichbar oder Zeitlimit überschritten "
            f"({type(exc).__name__}). Überspringe KI-Antwort-Extraktion, "
            "der Fragebogen wird ohne Vorbefüllung fortgesetzt."
        )
        return {"_error": "KI-Agent ist derzeit nicht verfügbar."}
    except json.JSONDecodeError as exc:
        log_info(f"KI-Antwort war kein gültiges JSON: {exc} – Rohtext: {raw!r}")
        return {}
    except Exception as exc:
        import traceback

        log_info(
            "Fehler bei der KI-Antwort-Extraktion: "
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )
        return {"_error": "KI-Agent ist derzeit nicht verfügbar."}
