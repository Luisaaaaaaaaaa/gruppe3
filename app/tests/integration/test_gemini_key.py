"""Eigenstaendiger Test der Gemini-REST-API ohne das google-genai-Paket.

Nutzt nur die Python-Standardbibliothek (urllib). Liest GEMINI_API_KEY aus
der .env und ruft denselben Endpunkt auf, den auch das SDK verwendet.

Ausfuehren:  python test_gemini_key.py
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "gemini-2.0-flash"
ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
)


def _load_key() -> str:
    # Vom Skript aus nach oben laufen, bis eine .env gefunden wird
    # (funktioniert unabhaengig davon, wie tief das Skript liegt).
    for parent in Path(__file__).resolve().parents:
        env_path = parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GEMINI_API_KEY") and "=" in line:
                    return line.split("=", 1)[1].strip()
            break
    return os.environ.get("GEMINI_API_KEY", "")


def main() -> None:
    key = _load_key()
    if not key:
        print("FEHLER: Kein GEMINI_API_KEY in .env gefunden.")
        return
    if key.upper().startswith("DEIN") or len(key) < 30:
        print(f"WARNUNG: Key sieht wie ein Platzhalter aus (Laenge {len(key)}, beginnt mit '{key[:4]}').")
        print("Trage zuerst einen echten Key in die .env ein (beginnt meist mit 'AIza').\n")

    payload = json.dumps(
        {"contents": [{"parts": [{"text": "Antworte nur mit dem Wort: OK"}]}]}
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{ENDPOINT}?key={key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        print("ERFOLG: Die API antwortet.")
        print("Antwort:", text.strip())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        print(f"HTTP-FEHLER {exc.code}: {exc.reason}")
        print("Details:", detail)
        if exc.code in (400, 403):
            print(">> Wahrscheinlich ungueltiger oder nicht freigeschalteter API-Key.")
    except urllib.error.URLError as exc:
        print(f"VERBINDUNGSFEHLER: {exc.reason}")
        print(">> Vermutlich blockiert die Firewall den Zugriff auf googleapis.com.")
    except Exception as exc:  # noqa: BLE001
        print(f"UNERWARTETER FEHLER: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
