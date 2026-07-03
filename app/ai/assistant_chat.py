from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from app.logger.audit_logger import log_info

if TYPE_CHECKING:
    from app.scenarios.hypertension_scenario import AnamnesisQuestion


# Konfiguration des LLM-Endpunkts. Identisch zu app/ai/symptom_extractor.py,
# damit derselbe selbst-gehostete, OpenAI-kompatible Server genutzt wird.
# Per .env überschreibbar: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL.
_DEFAULT_BASE_URL = "http://141.19.87.240:8000/v1"
_DEFAULT_API_KEY = "local-dev-key"
_DEFAULT_MODEL = "deepseek-v4-pro"

# Zeitlimit (Sekunden) pro LLM-Aufruf. Ist der Server nicht erreichbar oder
# antwortet er nicht, schlaegt der Aufruf nach dieser Zeit fehl, statt den
# Chat blockieren zu lassen. Per .env ueberschreibbar: LLM_TIMEOUT.
_DEFAULT_TIMEOUT_SECONDS = 15.0

# Freundliche Ausweich-Antwort, falls die KI-Schnittstelle nicht erreichbar ist.
# Oeffentlich, damit die Oberflaeche diesen Zustand erkennen und einen
# entsprechenden Hinweis anzeigen kann.
OFFLINE_REPLY = (
    "Entschuldigung, ich kann Ihre Frage gerade nicht beantworten, "
    "da die Verbindung zum Assistenzsystem nicht verfügbar ist. "
    "Bitte füllen Sie den Fragebogen nach bestem Wissen aus – das "
    "Praxisteam hilft Ihnen anschließend gerne weiter."
)


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


def _build_context_block(
    questions: list[AnamnesisQuestion],
    answers: dict[str, str],
) -> str:
    """Kompakte Übersicht 'Frage → aktuelle Antwort' für den KI-Kontext."""
    if not questions:
        return "Es liegen aktuell keine Fragebogen-Fragen vor."

    lines = []
    for q in questions:
        answer = str(answers.get(q.key, "")).strip()
        answer_text = answer if answer else "(noch nicht beantwortet)"
        lines.append(f"- {q.text} → {answer_text}")
    return "\n".join(lines)


def answer_question(
    user_message: str,
    questions: list[AnamnesisQuestion],
    answers: dict[str, str],
    history: list[tuple[str, str]],
) -> str:
    """Beantwortet eine Patientenfrage zum Anamnese-Fragebogen.

    history ist eine Liste von (role, text)-Tupeln früherer Nachrichten,
    wobei role "user" oder "system"/"assistant" ist.
    """
    if not user_message.strip():
        return ""

    base_url = os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", _DEFAULT_API_KEY)
    model = os.environ.get("LLM_MODEL", _DEFAULT_MODEL)

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=_request_timeout_seconds(),
            max_retries=0,
        )
    except ImportError:
        log_info(
            "openai-Bibliothek nicht installiert (pip install openai), "
            "Hilfe-Chat nicht verfügbar."
        )
        return OFFLINE_REPLY
    except Exception as exc:
        log_info(
            "Fehler beim Erstellen des KI-Clients (Hilfe-Chat): "
            f"{type(exc).__name__}: {exc}"
        )
        return OFFLINE_REPLY

    context_block = _build_context_block(questions, answers)

    system_prompt = (
        "Du bist ein freundlicher, geduldiger Assistent in einer Hausarztpraxis. "
        "Du hilfst einem Patienten beim Ausfüllen eines Anamnese-Fragebogens. "
        "Deine Aufgabe ist es, Fragen des Patienten zu beantworten – zum Beispiel "
        "schwierige medizinische Begriffe einfach zu erklären oder zu erläutern, "
        "was mit einer Frage gemeint ist.\n\n"
        "Wichtige Regeln:\n"
        "- Antworte immer auf Deutsch, kurz und in einfacher, verständlicher Sprache.\n"
        "- Stelle KEINE Diagnose und gib KEINE Therapie- oder Medikamentenempfehlung. "
        "Verweise dafür freundlich auf die Ärztin oder den Arzt.\n"
        "- Nutze den Fragebogen und die bisherigen Antworten als Kontext, um gezielt "
        "zu helfen.\n"
        "- Wenn du etwas nicht weißt, sage das ehrlich.\n\n"
        "Aktueller Fragebogen mit den bisherigen Antworten des Patienten:\n"
        f"{context_block}"
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    for role, text in history:
        if not text or not text.strip():
            continue
        normalized = "user" if role == "user" else "assistant"
        messages.append({"role": normalized, "content": text})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=500,
        )

        reply = response.choices[0].message.content
        if not reply or not reply.strip():
            log_info(
                "Hilfe-Chat: KI-Antwort enthielt keinen Text. "
                f"Vollständige Antwort: {response!r}"
            )
            return OFFLINE_REPLY

        return reply.strip()

    except Exception as exc:
        import traceback

        log_info(
            "Fehler im Hilfe-Chat: "
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )
        return OFFLINE_REPLY
