import random

class Simulator:
    def __init__(
        self,
        geschlecht: str = "divers",
        groesse_cm: int = 173,
        alter: int = 18
    ) -> None:
        """
        Parameters:
        - geschlecht: 'männlich', 'weiblich', 'divers'
        - groesse_cm: Körpergröße in cm
        - alter: Alter in Jahren
        """

        self.geschlecht: str = geschlecht.lower()
        self.groesse_cm: int = groesse_cm
        self.alter: int = alter

    def gewicht(self) -> dict[str, float | str]:
        """
        Quelle: https://adipositas-gesellschaft.de/bmi/

        Gewicht abhängig von:
        - Alter
        - BMI / BMI-Perzentilen
        - Geschlecht
        - Größe
        """

        # =========================
        # KINDER / JUGENDLICHE
        # =========================
        if self.alter < 18:

            bmi_kategorien = [
                ((13.0, 17.9), "Untergewicht", 10),
                ((18.0, 22.5), "Normalgewicht", 80),
                ((22.6, 26.0), "Übergewicht", 7),
                ((26.1, 40.0), "Adipositas", 3),
            ]

        # =========================
        # ERWACHSENE
        # =========================
        else:

            bmi_kategorien = [
                ((15.0, 18.4), "Untergewicht", 2.2),
                ((18.5, 24.9), "Normalgewicht", 44.4),
                ((25.0, 29.9), "Übergewicht", 35.5),
                ((30.0, 50.0), "Adipositas", 17.9),
            ]

        bmi_bereich, bmi_klasse, _ = random.choices(
            population=bmi_kategorien,
            weights=[k[2] for k in bmi_kategorien]
        )[0]

        bmi: float = random.uniform(*bmi_bereich)

        groesse_m: float = self.groesse_cm / 100
        gewicht: float = bmi * (groesse_m ** 2)

        # Geschlechtsabhängige Anpassung
        if self.geschlecht == "männlich":
            gewicht *= 1.05
        elif self.geschlecht == "weiblich":
            gewicht *= 0.95


        return {
            "gewicht": round(gewicht, 1),
            "bmi": round(bmi, 1),
            "klasse": bmi_klasse
        }

    def pulsoximeter(self) -> dict[str, int]:
        """
        Simuliert:
        - SpO2 (Sauerstoffsättigung)
        - Ruhe-Puls
        unter Berücksichtigung des Alters
        """

        # SpO2
        spo2: int = random.choices(
            population=[
                random.randint(95, 100),  # normal
                random.randint(90, 94),   # zu gering
                random.randint(70, 89),   # kritisch
            ],
            weights=[95, 4.5, 0.5]        # selbst gewählte Werte
        )[0]

        # Normalpuls altersabhängig
        if self.alter < 18:
            puls_normal = (85, 100)
        else:
            puls_normal = (70, 73)
            puls_gut = (40, 69)
            puls_unterdurchschnittlich = (74, 80)
            puls_schlecht = (80, 100)

        # Frauen leicht höherer Puls
        if self.geschlecht == "weiblich":
            puls_normal = (
                puls_normal[0] + 5,
                puls_normal[1] + 5
            )
            puls_gut = (
                puls_gut[0] + 5,
                puls_gut[1] + 5
            )
            puls_unterdurchschnittlich = (
                puls_unterdurchschnittlich[0] + 5,
                puls_unterdurchschnittlich[1] + 5
            )
            puls_schlecht = (
                puls_schlecht[0] + 5,
                puls_schlecht[1] + 5
            )
            

        puls: int = random.choices(
            population=[
                random.randint(*puls_normal),
                random.randint(*puls_gut),
                random.randint(*puls_unterdurchschnittlich),
                random.randint(*puls_schlecht)
            ],
            weights=[78, 15, 5, 2]      # selbst gewählte Werte
        )[0]

        return {
            "spo2": spo2,
            "puls": puls
        }

    def blutdruck(self) -> dict[str, int]:
        """
        Blutdruck abhängig von:
        - Geschlecht
        - Größe
        - Alter
        """

        # Altersabhängige Normalwerte
        if self.alter < 19:             # Alter 6-19
            sys_normal = (100, 115)     # Abweichung von 5
        else:
            sys_normal = (115, 139)     # Abeweichung von 5

        # Männer leicht höher
        if self.geschlecht == "männlich":
            sys_normal = (
                sys_normal[0] + 5,
                sys_normal[1] + 5
            )

        systolisch: int = random.choices(
            population=[
                random.randint(*sys_normal),
                random.randint(140, 160),   # Hypertonie Grad 1
                random.randint(161, 189)    # Hyptertonie Grad 2+3
            ],
            weights=[90, 8.5, 1.5]             # Selbst gewählte Werte
        )[0]

        diastolisch: int = random.choices(
            population=[
                random.randint(70, 89),     # Normal
                random.randint(90, 99),     # Hypertonie Grad 1
                random.randint(100, 119)    # Hypertonie Grad 2+3
            ],
            weights=[90, 8, 2]
        )[0]

        return {
            "systolisch": systolisch,
            "diastolisch": diastolisch
        }

    @staticmethod
    def simuliere_puls() -> int:
        """Realistischer Ruhepuls 60-100 bpm"""
        return random.randint(60, 100)

    @staticmethod
    def simuliere_blutdruck() -> dict[str, int]:
        """Realistischer Blutdruck: systolisch 110-160, diastolisch 60-100"""
        return {
            "systolisch": random.randint(110, 160),
            "diastolisch": random.randint(60, 100),
        }


# Beispiel
if __name__ == "__main__":

    sim1 = Simulator(
        geschlecht="männlich",
        groesse_cm=185,
        alter=72
    )

    print("=== Patient 1 ===")

    gewicht = sim1.gewicht()

    print(
        f"Gewicht:\t {gewicht['gewicht']} kg "
        f"(BMI: {gewicht['bmi']} - {gewicht['klasse']})"
    )

    print("Pulsoximeter:\t", sim1.pulsoximeter())
    print("Blutdruck:\t", sim1.blutdruck())

    ############################################################

    print("\n=== Patient 2 ===")

    sim2 = Simulator()

    gewicht2 = sim2.gewicht()

    print(
        f"Gewicht:\t {gewicht2['gewicht']} kg "
        f"(BMI: {gewicht2['bmi']} - {gewicht2['klasse']})"
    )

    print("Pulsoximeter:\t", sim2.pulsoximeter())
    print("Blutdruck:\t", sim2.blutdruck())