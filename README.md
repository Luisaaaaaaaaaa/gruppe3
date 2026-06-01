# SET Semesterprojekt (Gruppe 3)

Dieses Repository enthaelt einen prototypischen KI-gestuetzten Anamnese-Agenten fuer die hausarztpraxisnahe Lehre. Das System fuehrt mit synthetischen Patientendaten eine strukturierte Voranamnese durch, erkennt szenariospezifische Warnzeichen, erfasst Vitalparameter ueber Simulatoren und erstellt eine strukturierte Zusammenfassung fuer aerztliches Personal.

Das System ist ausdruecklich ein Assistenz-, Demonstrations- und Ausbildungssystem. Es stellt keine Diagnose, gibt keine Therapieempfehlung und ersetzt keine aerztliche Bewertung.

## Ziel und aktueller Funktionsumfang

Aktuell sind vier Standardszenarien im Projekt vorgesehen:

- `Szenario A`: Akuter Husten / Atemwegsinfekt / Verdacht auf Pneumonie
- `Szenario B`: Brustschmerz in der Hausarztpraxis
- `Szenario C`: Hypertonie-Kontrolle / auffaelliger Blutdruckwert
- `Szenario D`: Typ-2-Diabetes / metabolische Verlaufskontrolle

Bereits umgesetzt oder vorbereitet sind:

- Import synthetischer Patientendaten
- Auswahl eines Patienten aus der Tagesliste
- Identitaetspruefung
- Rollenerklaerung und Zustimmung
- strukturierte szenarioabhaengige Anamnese
- Geraetesimulatoren fuer Blutdruck, Gewicht und Pulsoximetrie
- regelbasierte Red-Flag-Erkennung
- strukturierte JSON-Zusammenfassung fuer die Uebergabe

## Diabetes-Szenario

Das Diabetes-Szenario orientiert sich an der Aufgabenstellung `Typ-2-Diabetes / metabolische Verlaufskontrolle` und ist bewusst als Verlaufskontrolle, nicht als Akutszenario, modelliert.

Erfasst werden unter anderem:

- bekannte Diagnosen und Vorerkrankungen
- aktuelle Medikamente
- Hinweise auf Hypoglykaemie oder Hyperglykaemie
- aktuelles Gewicht und Gewichtsveraenderungen
- Blutdruckwerte
- Lebensstilfaktoren
- bekannte Folgeerkrankungen und Komplikationen
- bekannte Vorbefunde wie HbA1c, letzter Blutzuckerwert und letzte Kontrolle
- offene Fragen an das aerztliche Personal

Zusatzlogik im Diabetes-Szenario:

- kontextabhaengige Folgefragen bei Symptomen, Gewichtsveraenderung, Komplikationen, Vorbefunden und Fussproblemen
- Red-Flags fuer schwere Stoffwechselentgleisung, kritische Blutdruckwerte und diabetische Fussprobleme
- lesbar gruppierte Zusammenfassung in den Bereichen `Verlauf`, `Aktuelle Symptome`, `Medikation`, `Komplikationen`, `Vorbefunde` und `Offene Fragen`
- didaktischer Zusatzblock `Diabetes-Verlaufsuebersicht` ohne Diagnose oder Therapieempfehlung

Wichtig:

- Es gibt bewusst keinen Blutzucker-Simulator.
- Ein letzter bekannter Blutzuckerwert wird nur als Patientenangabe dokumentiert.
- Die Verlaufsuebersicht dient ausschliesslich der strukturierten Dokumentation.

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

## Start

Programm starten:

```bash
python app/main.py
```

Die Anwendung startet nun als lokale Weboberflaeche mit NiceGUI und ist standardmaessig unter `http://127.0.0.1:8080` erreichbar.

## Projektstruktur

Wichtige Verzeichnisse und Dateien:

- `app/scenarios/`: Szenariodefinitionen und szenariospezifische Hilfslogik
- `app/dialogue/`: Dialogsteuerung und Zustandsautomat
- `app/medical_rules/`: Red-Flag-Erkennung
- `app/devices/`: Geraetesimulatoren
- `app/output/`: strukturierte Zusammenfassungen und Export
- `app/ui/`: grafische Oberflaeche auf Basis von NiceGUI

## Aktuell umgesetzt

- Szenarioauswahl fuer A bis D in der UI
- lokale NiceGUI-Weboberflaeche mit parallelen Browser-Sitzungen
- Diabetes-Szenario als eigene Fragenliste mit Pflichtfragen und optionalen Folgefragen
- Einbindung von `Szenario D` in den `dialogue_controller`
- Diabetes-spezifische Red-Flags mit `warning` und `critical`
- didaktischer Diabetes-Zusatzblock in der Ausgabemaske
- lesbarere Gruppierung der Diabetes-Zusammenfassung
- Validierung fuer numerische Eingaben vom Typ `zahl`

## Was noch ausgebaut werden sollte

- echte Auswahl zwischen manueller und simulierter Gewichtserfassung im Dialog
- konsequente Validierung plausibler Wertebereiche fuer alle numerischen Felder
- gezielte Unit-Tests fuer das Diabetes-Szenario und die neuen Red-Flag-Regeln
- Markdown- oder HTML-Export der strukturierten Zusammenfassung
- einheitlich sprechende Feldnamen in allen Szenarien und Exporten
- bessere Nutzung vorhandener Patientenvorinformationen fuer Szenario-Vorauswahl und Vorbefunde
- allgemeine Folgefragen-Logik auch fuer die anderen Szenarien

## Bekannte Grenzen

- keine medizinische Bewertung, keine Diagnose, keine Therapieaenderung
- ausschliesslich synthetische Daten
- Diabetes-Vorbefunde beruhen auf Patientenaussagen
- Folgefragen sind derzeit als regelbasierte Logik fuer Diabetes umgesetzt, nicht als vollstaendige generische Regel-Engine
- Gewicht wird im Diabetes-Szenario aktuell manuell erfragt; ein simulatorgestuetzter Umschaltpfad ist noch nicht eingebaut

## Test- und Ausbauideen

Sinnvolle naechste Schritte:

- Unit-Tests fuer `check_diabetes`
- Tests fuer Gruppierung und Ausgabe der Diabetes-Zusammenfassung
- Integrationstest fuer einen unkritischen Routinefall
- Integrationstest fuer einen Fall mit Red Flag und Eskalation
- Integrationstest fuer unvollstaendige oder unbekannte Vorbefunde

## Sicherheitshinweis

Alle Ausgaben sind als Demonstrations- und Assistenzfunktion zu verstehen. Kritische Konstellationen muessen immer an aerztliches Personal uebergeben werden.
