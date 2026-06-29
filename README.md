# SET Semesterprojekt (Gruppe 3)

Dieses Repository enthaelt einen prototypischen KI-gestuetzten Anamnese-Agenten fuer die hausarztpraxisnahe Lehre. Das System fuehrt mit synthetischen Patientendaten eine strukturierte Voranamnese durch, erkennt szenariospezifische Warnzeichen, erfasst Vitalparameter ueber Simulatoren und erstellt eine strukturierte Zusammenfassung fuer aerztliches Personal.

Das System ist ausdruecklich ein Assistenz-, Demonstrations- und Ausbildungssystem. Es stellt keine Diagnose, gibt keine Therapieempfehlung und ersetzt keine aerztliche Bewertung. Alle Bildschirmtexte sind auf Deutsch.

## Sicherheitshinweis

Alle Daten sind synthetisch; es werden keine realen Patientendaten verarbeitet. Saemtliche Ausgaben sind als Demonstrations- und Assistenzfunktion zu verstehen. Kritische Konstellationen muessen immer an aerztliches Personal uebergeben werden. Jeder Export wird als synthetisches Trainingsdokument gekennzeichnet.

## Funktionsumfang

- Vier Standardszenarien (A bis D), gesteuert ueber einen gemeinsamen Dialog-Zustandsautomaten
- Zwei Betriebsmodi: Patientenmodus (Selbstanmeldung) und Personalmodus (Tagesliste, Patientenverwaltung, vorbereitete Szenarien)
- Mehrfachauswahl: mehrere Szenarien koennen in einer Sitzung gemeinsam durchlaufen werden
- KI-gestuetzte Vorab-Erfassung der Beschwerden und ein KI-Hilfe-Chat zum Fragebogen (optional, mit Fallback)
- Sprachausgabe der Fragen und optionale Spracheingabe der Antworten
- Eulen-Avatar als visueller Assistent mit Zustands- und Sprechanimation
- Geraetesimulatoren fuer Blutdruck, Gewicht/BMI und Pulsoximetrie
- Regelbasierte Red-Flag-Erkennung mit sofortiger Eskalation bei kritischen Werten
- Strukturierte Zusammenfassung mit Export als JSON und PDF
- Identitaetspruefung mit begrenzten Anmeldeversuchen
- Szenario-Empfehlung anhand der hinterlegten Vorerkrankungen

## Szenarien

- `Szenario A`: Akuter Husten / Atemwegsinfekt / Verdacht auf Pneumonie (`cough`)
- `Szenario B`: Brustschmerz in der Hausarztpraxis (`chest_pain`)
- `Szenario C`: Hypertonie-Kontrolle / auffaelliger Blutdruckwert (`hypertension`)
- `Szenario D`: Typ-2-Diabetes / metabolische Verlaufskontrolle (`diabetes`)

Jedes Szenario besitzt eine eigene Fragenliste mit Pflicht- und optionalen Fragen. Der Fragenkatalog wird zur Laufzeit dynamisch aufgebaut: Er beruecksichtigt die in der Akte hinterlegten Vorerkrankungen, Risikofaktoren und Medikamente und ergaenzt szenarioabhaengige Folgefragen. Die Folgefragen-Logik ist fuer alle vier Szenarien umgesetzt.

## Betriebsmodi

### Patientenmodus

```bash
python app/main.py
```

Die Anwendung startet als lokale Weboberflaeche mit NiceGUI und ist standardmaessig unter `http://127.0.0.1:8080` erreichbar. Patientinnen und Patienten melden sich mit Vorname, Nachname und Geburtsdatum an und waehlen anschliessend ihre Szenarien.

### Personalmodus

```bash
python app/main_personal.py
```

Der Personalmodus startet standardmaessig unter `http://127.0.0.1:8081`. Praxispersonal kann hier einen Patienten aus der Tagesliste suchen und auswaehlen, Patientendaten anlegen oder bearbeiten und ein oder mehrere Szenarien vorbereiten. Danach startet direkt der Patientenmodus mit den vorbereiteten Szenarien, ohne erneute Anmeldung. Vorbereitete Szenarien werden in der Patientendatei gespeichert.

## KI-Funktionen (LLM)

Das System nutzt einen OpenAI-kompatiblen Endpunkt fuer zwei unabhaengige Funktionen:

- Vorab-Erfassung: Die freie Schilderung der Beschwerden wird ausgewertet und der Fragebogen so weit wie moeglich vorausgefuellt.
- Hilfe-Chat: Waehrend des Ausfuellens koennen Fragen zum Fragebogen oder zu Begriffen gestellt werden.

Beide Funktionen sind optional und arbeiten ausfallsicher. Ist der Server nicht erreichbar oder antwortet er nicht innerhalb des Zeitlimits, laeuft das Programm weiter: Die Vorab-Auswertung wird uebersprungen und der Fragebogen manuell ausgefuellt; der Hilfe-Chat zeigt einen Hinweis, dass der Assistent zurzeit nicht erreichbar ist.

Die Konfiguration erfolgt ueber Umgebungsvariablen, die auch aus einer `.env` im Projektwurzelverzeichnis gelesen werden:

- `LLM_BASE_URL` – Basis-URL des Endpunkts
- `LLM_API_KEY` – API-Schluessel
- `LLM_MODEL` – Modellname
- `LLM_TIMEOUT` – Zeitlimit pro Aufruf in Sekunden (Standard 15)

Ohne gesetzte Variablen werden Standardwerte fuer einen selbst gehosteten Server verwendet. Die Erreichbarkeit laesst sich separat pruefen:

```bash
python -m app.tests.integration.test_llm_endpoint
```

## Sprachausgabe und Spracheingabe

Im gefuehrten Gespraech kann der Assistent die Fragen vorlesen (Browser-Sprachausgabe ueber `speechSynthesis`). Die Sprachausgabe laesst sich ein- und ausschalten. Antworten und die Beschwerdeschilderung koennen alternativ per Mikrofon diktiert werden (Spracherkennung des Browsers, getestet in Chrome und Edge).

## Avatar-Verhalten

Die Weboberflaeche nutzt einen neutralen Eulen-Avatar als freundlichen, aber medizinisch-professionellen Assistenten. Er erscheint unter anderem bei der Auswahl des Anamnese-Modus, im Beschwerde-Chat und im Hilfe-Chat.

Der Avatar hat folgende Zustaende:

- `neutral`: Wird angezeigt, wenn noch kein Dialog aktiv ist oder die Rollenerklaerung beziehungsweise Einwilligung laeuft.
- `hoert zu`: Wird im gefuehrten Gespraech angezeigt, wenn der Avatar die Fragen nacheinander stellt.
- `spricht`: Wird waehrend der Sprachausgabe aktiviert. Kopf und Schnabel bewegen sich.
- `denkt nach`: Wird im Formularmodus und als allgemeiner Zwischenzustand angezeigt.
- `warnt`: Wird bei Red-Flag-Pruefung oder Eskalation angezeigt.
- `freut sich`: Wird bei Zusammenfassung, Uebergabe und Abschluss angezeigt.

Die Sprechanimation wird automatisch durch die Browser-Sprachausgabe gesteuert: Sobald die Stimme startet, setzt die UI den Zustand `avatar-is-speaking`; am Ende der Sprachausgabe wird er wieder entfernt.

## Geraetesimulatoren

Blutdruck, Gewicht/BMI und Pulsoximetrie (SpO2 und Puls) koennen ueber Simulatoren erfasst werden. Die Werte sind zufaellig, aber plausibel und beruecksichtigen Geschlecht, Groesse und Alter. Simulierte Messwerte werden mit Quellenangabe in die Zusammenfassung uebernommen und fliessen in die Red-Flag-Pruefung ein.

Bewusst gibt es **keinen** Blutzucker-Simulator: Ein letzter bekannter Blutzucker- oder HbA1c-Wert wird im Diabetes-Szenario nur als Patientenangabe dokumentiert.

## Red-Flag-Erkennung und Eskalation

Die regelbasierte Erkennung prueft Antworten und Vitalparameter szenariospezifisch und liefert Warnhinweise mit den Schweregraden `warning` und `critical`. Ein `critical`-Befund loest eine sofortige Eskalation aus und beendet die Routine-Anamnese unmittelbar. Die Pruefung erfolgt inkrementell, also bereits nach einzelnen Antworten und nach Geraetemessungen, nicht erst am Ende.

## Ausgabe und Export

Die Ergebnisdarstellung ist abschnittsweise gegliedert und fuer die aerztliche Uebergabe gedacht. Die strukturierte Zusammenfassung kann exportiert werden als:

- JSON (Ablage im Verzeichnis `output/`)
- PDF (zum Download, gerendert mit reportlab)

Jeder Export wird als synthetisches Trainingsdokument gekennzeichnet.

## Installation

Repository klonen:

```bash
git clone https://github.com/Luisaaaaaaaaaa/gruppe3.git
cd gruppe3
```

Conda-Umgebung erstellen und Abhaengigkeiten installieren:

```bash
conda create -n SET python=3.12
conda activate SET
pip install -r requirements.txt
```

Abhaengigkeiten (`requirements.txt`): `nicegui`, `openai`, `reportlab`.

## Tests

Die Tests werden mit pytest aus dem Projektwurzelverzeichnis ausgefuehrt (keine Konfigurationsdatei noetig):

```bash
python -m pytest                                       # alle Tests
python -m pytest app/tests/unit                        # nur Unit-Tests
python -m pytest app/tests/unit/test_cough_scenario.py # einzelne Datei
```

Abgedeckt sind unter anderem Szenarien, Red-Flag-Regeln, Zustandsautomat, Identitaetspruefung, Patientenimport, Simulatoren, Zusammenfassung und Export sowie Integrationstests fuer einen unkritischen Routinefall, eine kritische Eskalation, einen Abbruch und eine abgelehnte Einwilligung.

## Projektstruktur

- `app/scenarios/`: Szenariodefinitionen und szenariospezifische Hilfslogik
- `app/dialogue/`: Dialogsteuerung und Zustandsautomat
- `app/medical_rules/`: Red-Flag-Erkennung und Szenario-Empfehlung
- `app/devices/`: Geraetesimulatoren und Adapter
- `app/ai/`: KI-Vorab-Auswertung und Hilfe-Chat
- `app/patient_import/`: Einlesen und Schreiben der Patientendaten
- `app/output/`: strukturierte Zusammenfassung und Export (JSON, PDF)
- `app/identity/`: Identitaetspruefung und Namensnormalisierung
- `app/logger/`: Audit-Logging
- `app/ui/`: Weboberflaeche auf Basis von NiceGUI
- `app/main.py`: Patienteneinstieg mit Selbstanmeldung und Szenarioauswahl
- `app/main_personal.py`: Personaleinstieg mit Tagesliste, Patientenverwaltung und vorbereiteter Szenarioauswahl

## Bekannte Grenzen

- keine medizinische Bewertung, keine Diagnose, keine Therapieaenderung
- ausschliesslich synthetische Daten
- Vorbefunde (zum Beispiel HbA1c oder Blutzucker) beruhen auf Patientenaussagen
- die KI-Funktionen sind optional; bei fehlender Erreichbarkeit laeuft das System ohne sie weiter
- die Folgefragen-Logik ist regelbasiert je Szenario umgesetzt, nicht als generische Regel-Engine
