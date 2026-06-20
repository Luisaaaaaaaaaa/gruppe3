from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.medical_rules.red_flag_engine import RedFlag
from app.patient_import.patient_schema import PatientRecord


@dataclass
class AnamnesisSummary:
    patient_id: str
    patient_name: str
    scenario: str
    timestamp: str
    answers: dict[str, str] = field(default_factory=dict)
    vitals: dict[str, int | float] = field(default_factory=dict)
    vitals_source: str = "simuliert"
    red_flags: list[RedFlag] = field(default_factory=list)
    escalation_required: bool = False
    open_points: list[str] = field(default_factory=list)
    grouped_sections: dict[str, dict[str, str]] = field(default_factory=dict)
    synthetic: bool = True


def build_summary(
    patient: PatientRecord,
    scenario: str,
    answers: dict[str, str],
    vitals: dict | None = None,
    vitals_source: str = "simuliert",
    red_flags: list[RedFlag] | None = None,
) -> AnamnesisSummary:
    if red_flags is None:
        red_flags = []

    if vitals is None:
        vitals = {}

    escalation_required = any(rf.severity == "critical" for rf in red_flags)

    _ignored_keys = frozenset({
        "blutdruck_messen",
        "blutdruck_diastolisch",
        "puls_messen",
        "gewicht_messen",
    })

    open_points = [
        f"Angabe zu '{key}' fehlt oder unbekannt."
        for key, value in answers.items()
        if key not in _ignored_keys
        and (not value.strip() or value.strip().lower() == "unbekannt")
    ]

    grouped_sections = build_grouped_sections(
        scenario, answers, vitals, patient.medications
    )

    return AnamnesisSummary(
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        scenario=scenario,
        timestamp=datetime.now().isoformat(),
        answers=answers,
        vitals=vitals,
        vitals_source=vitals_source,
        red_flags=red_flags,
        escalation_required=escalation_required,
        open_points=open_points,
        grouped_sections=grouped_sections,
    )


def build_grouped_sections(
    scenario: str,
    answers: dict[str, str],
    vitals: dict,
    patient_medications: list[str] | None = None,
) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}

    if answers.get("vorerkrankungen_aktuell", "").strip():
        sections["Vorerkrankungen / Risikofaktoren (aktueller Stand)"] = {
            "Allgemein": answers.get("vorerkrankungen_aktuell", "")
        }

    if scenario in ("A", "cough"):
        def add_section(title: str, fields: dict[str, str]) -> None:
            non_empty = {key: value for key, value in fields.items() if value.strip()}
            if non_empty:
                sections[title] = non_empty

        add_section("Beginn und Verlauf", {
            "Dauer der Beschwerden": answers.get("symptom_dauer", ""),
            "Rasche Verschlechterung": answers.get("rasche_verschlechterung", ""),
        })
        add_section("Husten und Schleim", {
            "Art des Hustens": answers.get("hustenart", ""),
            "Schleim beim Husten": answers.get("auswurf", ""),
            "Farbe des Schleims": answers.get("auswurf_farbe", ""),
            "Blut beim Husten": answers.get("blutbeimengung", ""),
        })
        add_section("Atmung und Brustbeschwerden", {
            "Kurzatmigkeit": answers.get("dyspnoe", ""),
            "Atemnot in Ruhe": answers.get("ruhedyspnoe", ""),
            "Luftholen beim Sprechen": answers.get("sprechen_beeintraechtigt", ""),
            "Kurzatmigkeit bei Belastung": answers.get("belastungsdyspnoe", ""),
            "Bläuliche Lippen oder Gesicht": answers.get("zyanose", ""),
            "Auffälliges Atemgeräusch": answers.get("auffaelliges_atemgeraeusch", ""),
            "Schmerzen oder Druck in der Brust": answers.get("thorakale_schmerzen", ""),
            "Schmerzen beim Atmen oder Husten": answers.get("atemabhaengige_schmerzen", ""),
        })
        add_section("Fieber und Allgemeinzustand", {
            "Fieber": answers.get("fieber", ""),
            "Höchste gemessene Temperatur": answers.get("korpertemperatur", ""),
            "Schüttelfrost": answers.get("schuettelfrost", ""),
            "Verwirrtheit": answers.get("verwirrtheit", ""),
            "Ohnmacht oder Beinahe-Zusammenbruch": answers.get("ohnmacht", ""),
            "Starke Schwäche": answers.get("reduzierter_allgemeinzustand", ""),
        })

        risks = {
            "Rauch oder reizende Dämpfe eingeatmet": answers.get("rauch_reizstoffe", ""),
            "Kürzliche Brustkorbverletzung": answers.get("brustverletzung", ""),
            "Dauerhafte Lungenerkrankung": answers.get("chronische_lungenerkrankung", ""),
            "Herzschwäche": answers.get("herzschwaeche", ""),
            "Stark geschwächte Abwehr": answers.get("immunschwaeche", ""),
            "Weitere Vorerkrankungen": answers.get("vorerkrankungen", ""),
            "Weitere Risiken": answers.get("risikofaktoren", ""),
            "Änderungen laut Patientenakte": answers.get("vorerkrankungen_aktuell", ""),
            "Vorerkrankungen laut Patientenakte": answers.get("vorerkrankungen_liste", ""),
        }
        for key, value in answers.items():
            if key.startswith("risikofaktor_"):
                risks[f"Risikofaktor {key.removeprefix('risikofaktor_')}"] = value
        add_section("Vorerkrankungen und Risiken", risks)

        medications = {}
        if answers.get("medikamente", "").strip():
            medications["Aktuelle Medikamente"] = answers["medikamente"]
        if answers.get("weitere_medikamente", "").strip():
            medications["Weitere oder gelegentlich eingenommene Medikamente"] = answers["weitere_medikamente"]
        for key, value in answers.items():
            if key.startswith("med_adhaerenz_grund_"):
                index = int(key.removeprefix("med_adhaerenz_grund_"))
                name = (
                    patient_medications[index]
                    if patient_medications and index < len(patient_medications)
                    else f"Medikament {index + 1}"
                )
                medications[f"Grund für abweichende Einnahme von {name}"] = value
            elif key.startswith("med_adhaerenz_"):
                index = int(key.removeprefix("med_adhaerenz_"))
                name = (
                    patient_medications[index]
                    if patient_medications and index < len(patient_medications)
                    else f"Medikament {index + 1}"
                )
                medications[f"{name} wie verordnet"] = value
        add_section("Medikamente", medications)

        measurements = {
            "Angegebene Atemzüge pro Minute": answers.get("atemfrequenz", ""),
        }
        vital_labels = {
            "temperatur": "Temperatur in °C",
            "atemfrequenz": "Atemzüge pro Minute",
            "spo2": "Sauerstoffsättigung in %",
            "puls": "Puls pro Minute",
        }
        for key, value in vitals.items():
            if key in vital_labels:
                measurements[vital_labels[key]] = str(value)
        add_section("Messwerte", measurements)

        return sections

    if scenario in ("B", "chest_pain"):
        def add_chest_section(title: str, fields: dict[str, str]) -> None:
            non_empty = {key: value for key, value in fields.items() if value.strip()}
            if non_empty:
                sections[title] = non_empty

        add_chest_section("Beginn und Verlauf", {
            "Ort der Schmerzen": answers.get("lokalisation", ""),
            "Beginn": answers.get("beginn", ""),
            "Plötzlicher Beginn": answers.get("ploetzlicher_beginn", ""),
            "Dauer": answers.get("dauer", ""),
            "Schmerzen aktuell": answers.get("schmerzen_aktuell", ""),
            "Stärke (0 bis 10)": answers.get("schmerzstaerke", ""),
            "Stärker oder häufiger geworden": answers.get("rasche_verschlechterung", ""),
            "Ähnliche Schmerzen früher": answers.get("aehnliche_schmerzen", ""),
        })
        add_chest_section("Art und Auslöser", {
            "Art der Schmerzen": answers.get("schmerzcharakter", ""),
            "Ziehen in andere Körperstellen": answers.get("ausstrahlung", ""),
            "Bei Anstrengung": answers.get("belastungsabhaengigkeit", ""),
            "Besserung in Ruhe": answers.get("ruhe_besserung", ""),
            "Bei Bewegung, Atmen oder Husten": answers.get("bewegung_atmung_husten", ""),
            "Durch Druck auslösbar": answers.get("druckschmerz_thoraxwand", ""),
            "Bei Essen oder Schlucken": answers.get("essen_schlucken", ""),
        })
        add_chest_section("Begleitende Beschwerden", {
            "Sodbrennen": answers.get("sodbrennen", ""),
            "Übelkeit oder Erbrechen": answers.get("uebelkeit", ""),
            "Schlechter Luft": answers.get("atemnot", ""),
            "Schlechter Luft in Ruhe": answers.get("ruhedyspnoe", ""),
            "Kaltes oder starkes Schwitzen": answers.get("kaltschweissigkeit", ""),
            "Ohnmacht oder Beinahe-Zusammenbruch": answers.get("synkope", ""),
            "Verwirrtheit oder starke Benommenheit": answers.get("verwirrtheit", ""),
            "Sehr starke Schwäche": answers.get("ausgepraege_schwaeche", ""),
        })

        risks = {
            "Patient vermutet das Herz als Ursache": answers.get("patient_vermutet_herz", ""),
            "Erkrankung von Herz oder Blutgefäßen": answers.get("bekannte_khk", ""),
            "Risikofaktoren": answers.get("kardiovaskulaere_risikofaktoren", ""),
            "Weitere Vorerkrankungen": answers.get("vorerkrankungen", ""),
            "Änderungen laut Patientenakte": answers.get("vorerkrankungen_aktuell", ""),
            "Vorerkrankungen laut Patientenakte": answers.get("vorerkrankungen_liste", ""),
        }
        for key, value in answers.items():
            if key.startswith("risikofaktor_"):
                risks[f"Risikofaktor {key.removeprefix('risikofaktor_')}"] = value
        add_chest_section("Vorerkrankungen und Risiken", risks)

        medications: dict[str, str] = {}
        if answers.get("medikamente", "").strip():
            medications["Aktuelle Medikamente"] = answers["medikamente"]
        if answers.get("weitere_medikamente", "").strip():
            medications["Weitere oder gelegentlich eingenommene Medikamente"] = answers["weitere_medikamente"]
        for key, value in answers.items():
            if key.startswith("med_adhaerenz_grund_"):
                index = int(key.removeprefix("med_adhaerenz_grund_"))
                name = (
                    patient_medications[index]
                    if patient_medications and index < len(patient_medications)
                    else f"Medikament {index + 1}"
                )
                medications[f"Grund für abweichende Einnahme von {name}"] = value
            elif key.startswith("med_adhaerenz_"):
                index = int(key.removeprefix("med_adhaerenz_"))
                name = (
                    patient_medications[index]
                    if patient_medications and index < len(patient_medications)
                    else f"Medikament {index + 1}"
                )
                medications[f"{name} wie verordnet"] = value
        add_chest_section("Medikamente", medications)

        vital_labels = {
            "systolisch": "Oberer Blutdruckwert",
            "diastolisch": "Unterer Blutdruckwert",
            "puls": "Puls pro Minute",
            "spo2": "Sauerstoffsättigung in %",
        }
        add_chest_section(
            "Messwerte",
            {vital_labels[key]: str(value) for key, value in vitals.items() if key in vital_labels},
        )
        return sections

    if scenario in ("C", "hypertension"):
        def add_hypertension_section(title: str, fields: dict[str, str]) -> None:
            non_empty = {key: value for key, value in fields.items() if value.strip()}
            if non_empty:
                sections[title] = non_empty

        add_hypertension_section("Anlass und Verlauf", {
            "Bluthochdruck bereits bekannt": answers.get("bluthochdruck_bekannt", ""),
            "Letzte ärztliche Kontrolle": answers.get("letzte_kontrolle", ""),
            "Behandlung seitdem verändert": answers.get("behandlung_geaendert", ""),
            "Zu Hause in den letzten sieben Tagen gemessen": answers.get("heimwerte_vorhanden", ""),
            "Verlauf der Werte zu Hause": answers.get("heimwerte_verlauf", ""),
            "Zeit und Ort des erstmals auffälligen Werts": answers.get("auffaelliger_wert_wann", ""),
            "Erneut gemessen": answers.get("mehrfach_gemessen", ""),
            "Frühere auffällige Werte": answers.get("fruehere_auffaellige_werte", ""),
        })

        measurement_fields = {
            "Messbedingungen": answers.get("messbedingungen", ""),
        }
        vital_labels = {
            "systolisch": "Oberer Blutdruckwert",
            "diastolisch": "Unterer Blutdruckwert",
            "puls": "Puls pro Minute",
            "gewicht": "Gewicht in kg",
        }
        for key, value in vitals.items():
            if key in vital_labels:
                measurement_fields[vital_labels[key]] = str(value)
        add_hypertension_section("Messwerte", measurement_fields)

        add_hypertension_section("Aktuelle Beschwerden und Warnzeichen", {
            "Schmerzen oder Druck in der Brust": answers.get("brustschmerz", ""),
            "Atemnot": answers.get("atemnot", ""),
            "Lähmung, Taubheitsgefühl oder Sprachprobleme": answers.get("neurologische_symptome", ""),
            "Plötzliche Sehprobleme": answers.get("sehstoerungen", ""),
            "Ungewöhnlich starke Kopfschmerzen": answers.get("kopfschmerz", ""),
            "Ohnmacht oder Beinahe-Zusammenbruch": answers.get("ohnmacht", ""),
            "Starkes oder unregelmäßiges Herzklopfen": answers.get("herzklopfen", ""),
        })

        risks = {
            "Weitere Vorerkrankungen": answers.get("vorerkrankungen", ""),
            "Änderungen laut Patientenakte": answers.get("vorerkrankungen_aktuell", ""),
            "Vorerkrankungen laut Patientenakte": answers.get("vorerkrankungen_liste", ""),
            "Rauchen und Alkohol": answers.get("rauchen_alkohol", ""),
            "Salz, Lakritz, Kaffee oder Energydrinks": answers.get("ernaehrung", ""),
            "Regelmäßige Bewegung": answers.get("bewegung", ""),
            "Starke Belastung oder Anspannung": answers.get("stress", ""),
            "Schnarchen, Atempausen oder Tagesmüdigkeit": answers.get("schlaf", ""),
        }
        for key, value in answers.items():
            if key.startswith("risikofaktor_"):
                risks[f"Risikofaktor {key.removeprefix('risikofaktor_')}"] = value
        add_hypertension_section("Vorerkrankungen und Lebensweise", risks)

        medications: dict[str, str] = {}
        if answers.get("medikamente", "").strip():
            medications["Aktuelle Medikamente"] = answers["medikamente"]
        if answers.get("weitere_medikamente", "").strip():
            medications["Weitere oder gelegentlich eingenommene Medikamente"] = answers["weitere_medikamente"]
        for key, value in answers.items():
            if key.startswith("med_adhaerenz_grund_"):
                index = int(key.removeprefix("med_adhaerenz_grund_"))
                name = patient_medications[index] if patient_medications and index < len(patient_medications) else f"Medikament {index + 1}"
                medications[f"Grund für abweichende Einnahme von {name}"] = value
            elif key.startswith("med_adhaerenz_"):
                index = int(key.removeprefix("med_adhaerenz_"))
                name = patient_medications[index] if patient_medications and index < len(patient_medications) else f"Medikament {index + 1}"
                medications[f"{name} wie verordnet"] = value
        add_hypertension_section("Medikamente", medications)
        return sections

    if scenario in ("D", "diabetes"):
        verlauf: dict[str, str] = {}

        gewicht = answers.get("gewicht_aktuell", "").strip()
        if gewicht and gewicht.lower() != "unbekannt":
            verlauf["Aktuelles Gewicht"] = f"{gewicht} kg"
        elif "gewicht" in vitals:
            verlauf["Aktuelles Gewicht"] = f"{vitals['gewicht']} kg"
        else:
            verlauf["Aktuelles Gewicht"] = "keine Angabe"

        gv = answers.get("gewichtsveraenderung", "").strip().lower()
        if gv in ("ja", "j", "yes", "y"):
            gv_details = answers.get("gewichtsveraenderung_details", "").strip()
            verlauf["Gewichtsveraenderung"] = gv_details if gv_details else "ja"
        else:
            verlauf["Gewichtsveraenderung"] = "keine angegeben"

        sys_val = answers.get("blutdruck_systolisch", "").strip()
        dia_val = answers.get("blutdruck_diastolisch", "").strip()

        if sys_val.lower() != "unbekannt" and sys_val:
            sys_str = sys_val
        elif "systolisch" in vitals:
            sys_str = str(vitals["systolisch"])
        else:
            sys_str = "unbekannt"

        if dia_val.lower() != "unbekannt" and dia_val:
            dia_str = dia_val
        elif "diastolisch" in vitals:
            dia_str = str(vitals["diastolisch"])
        else:
            dia_str = "unbekannt"

        verlauf["Blutdruck"] = f"{sys_str}/{dia_str} mmHg"

        heimwerte = answers.get("blutdruck_zu_hause_details", "").strip()
        if heimwerte:
            verlauf["Blutdruckwerte zu Hause"] = heimwerte

        verlauf["Letzte Diabetes-Kontrolle"] = answers.get("letzte_kontrolle", "")

        sections["Verlauf"] = verlauf

        symptome: dict[str, str] = {}
        symptom_fields = {
            "Allgemeinbefinden": "allgemeinbefinden",
            "Ungewöhnlich starker Durst": "starker_durst",
            "Häufigeres Wasserlassen": "haeufiges_wasserlassen",
            "Müdigkeit, Schwäche oder Benommenheit": "muedigkeit_schwaeche",
            "Zittern, Schwitzen, Herzklopfen, Hunger oder Schwindel": "hypo_hyper_hinweise",
            "Erbrechen, Bauchschmerz oder auffällige Atmung": "akutes_erbrechen_atmung",
            "Verwirrtheit, Ohnmacht oder Bewusstlosigkeit": "akut_verwirrt_bewusstlos",
            "Brustschmerz oder Druck in der Brust": "brustschmerz",
            "Atemnot": "atemnot",
            "Plötzliche Sehverschlechterung": "sehstoerungen",
        }
        for label, key in symptom_fields.items():
            value = answers.get(key, "")
            if value:
                symptome[label] = value
        hypo_details = answers.get("hypo_hyper_beschwerden", "")
        if hypo_details:
            symptome["Beschwerden"] = hypo_details
        sections["Aktuelle Symptome"] = symptome

        medikation: dict[str, str] = {}
        med_value = answers.get("medikamente", "")
        if med_value:
            medikation["Aktuelle Medikamente"] = med_value
        additional_med_value = answers.get("weitere_medikamente", "")
        if additional_med_value:
            medikation["Weitere oder gelegentlich eingenommene Medikamente"] = additional_med_value
        diag_value = answers.get("bekannte_diagnosen", "")
        if diag_value:
            medikation["Bekannte Diagnosen"] = diag_value
        for key, value in answers.items():
            if key.startswith("med_adhaerenz_grund_") and value:
                medikation[f"Grund für abweichende Einnahme ({key.removeprefix('med_adhaerenz_grund_')})"] = value
            elif key.startswith("med_adhaerenz_") and value:
                medikation[f"Einnahme wie vereinbart ({key.removeprefix('med_adhaerenz_')})"] = value
        sections["Medikation"] = medikation

        komplikationen: dict[str, str] = {}
        fe_bekannt = answers.get("folgeerkrankungen_bekannt", "")
        if fe_bekannt:
            komplikationen["Folgeerkrankungen bekannt"] = fe_bekannt
        fe_details = answers.get("folgeerkrankungen_details", "")
        if fe_details:
            komplikationen["Details"] = fe_details
        fuss = answers.get("offene_wunde_fussproblem", "")
        if fuss:
            komplikationen["Fussprobleme oder Wunden"] = fuss
        fuss_details = answers.get("offene_wunde_fussproblem_details", "")
        if fuss_details:
            komplikationen["Fussproblem-Details"] = fuss_details
        if answers.get("gefuehlsstoerungen_fuesse", ""):
            komplikationen["Kribbeln, Brennen, Schmerzen oder Taubheit"] = answers["gefuehlsstoerungen_fuesse"]
        sections["Komplikationen"] = komplikationen

        vorbefunde: dict[str, str] = {}
        hba1c_bek = answers.get("hba1c_bekannt", "")
        if hba1c_bek:
            vorbefunde["HbA1c bekannt"] = hba1c_bek
        hba1c_w = answers.get("hba1c_wert", "")
        if hba1c_w:
            vorbefunde["HbA1c-Wert"] = hba1c_w
        bz_bek = answers.get("blutzuckerwert_bekannt", "")
        if bz_bek:
            vorbefunde["Blutzuckerwert bekannt"] = bz_bek
        bz_w = answers.get("blutzuckerwert_details", "")
        if bz_w:
            vorbefunde["Blutzuckerwert"] = bz_w
        for key, label in (
            ("letzte_augenkontrolle", "Letzte Augenkontrolle"),
            ("letzte_fusskontrolle", "Letzte Fußkontrolle"),
            ("letzte_nierenkontrolle", "Letzte Nierenkontrolle"),
        ):
            if answers.get(key, ""):
                vorbefunde[label] = answers[key]
        sections["Vorbefunde"] = vorbefunde

        offene_fragen: dict[str, str] = {}
        of = answers.get("offene_fragen", "")
        if of:
            offene_fragen["Patientenfragen"] = of
        for key, label in (
            ("bewegung", "Bewegung"),
            ("ernaehrung", "Ernährung"),
            ("rauchen", "Rauchen"),
            ("alkohol_konsum", "Alkoholkonsum"),
            ("alkohol", "Alkohol"),
            ("alltag_belastung", "Belastung durch Diabetes im Alltag"),
            ("stimmung", "Stimmung"),
            ("hilfebedarf", "Hilfebedarf"),
        ):
            if answers.get(key, ""):
                offene_fragen[label] = answers[key]
        sections["Offene Fragen"] = offene_fragen

        if answers:
            sections["Anamnese"] = {k: v for k, v in answers.items() if v.strip()}

    return sections
