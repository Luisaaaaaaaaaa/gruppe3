"""Unit-Tests fuer Geraetesimulatoren (Blutdruck, Gewicht, Pulsoximeter)."""

import pytest

from app.devices.simulators import Simulator


class TestBlutdruckSimulator:
    def test_returns_systolisch_and_diastolisch(self) -> None:
        sim = Simulator(geschlecht="weiblich", groesse_cm=165, alter=45)
        result = sim.blutdruck()
        assert "systolisch" in result
        assert "diastolisch" in result

    def test_values_are_integers(self) -> None:
        sim = Simulator()
        result = sim.blutdruck()
        assert isinstance(result["systolisch"], int)
        assert isinstance(result["diastolisch"], int)

    def test_systolisch_in_plausible_range(self) -> None:
        sim = Simulator(geschlecht="männlich", groesse_cm=180, alter=60)
        for _ in range(50):
            result = sim.blutdruck()
            assert 80 <= result["systolisch"] <= 250

    def test_diastolisch_in_plausible_range(self) -> None:
        sim = Simulator()
        for _ in range(50):
            result = sim.blutdruck()
            assert 50 <= result["diastolisch"] <= 150

    def test_male_tends_higher(self) -> None:
        male_sim = Simulator(geschlecht="männlich", groesse_cm=180, alter=40)
        female_sim = Simulator(geschlecht="weiblich", groesse_cm=165, alter=40)
        male_values = [male_sim.blutdruck()["systolisch"] for _ in range(200)]
        female_values = [female_sim.blutdruck()["systolisch"] for _ in range(200)]
        assert sum(male_values) / len(male_values) > sum(female_values) / len(female_values) - 20


class TestPulsoximeter:
    def test_returns_spo2_and_puls(self) -> None:
        sim = Simulator()
        result = sim.pulsoximeter()
        assert "spo2" in result
        assert "puls" in result

    def test_values_are_integers(self) -> None:
        sim = Simulator()
        result = sim.pulsoximeter()
        assert isinstance(result["spo2"], int)
        assert isinstance(result["puls"], int)

    def test_spo2_in_valid_range(self) -> None:
        sim = Simulator()
        for _ in range(50):
            result = sim.pulsoximeter()
            assert 50 <= result["spo2"] <= 100

    def test_puls_in_valid_range(self) -> None:
        sim = Simulator(geschlecht="männlich", groesse_cm=175, alter=30)
        for _ in range(50):
            result = sim.pulsoximeter()
            assert 30 <= result["puls"] <= 200


class TestGewichtSimulator:
    def test_returns_gewicht_bmi_klasse(self) -> None:
        sim = Simulator(geschlecht="weiblich", groesse_cm=170, alter=35)
        result = sim.gewicht()
        assert "gewicht" in result
        assert "bmi" in result
        assert "klasse" in result

    def test_gewicht_is_float(self) -> None:
        sim = Simulator()
        result = sim.gewicht()
        assert isinstance(result["gewicht"], float)

    def test_bmi_is_float(self) -> None:
        sim = Simulator()
        result = sim.gewicht()
        assert isinstance(result["bmi"], float)

    def test_klasse_is_valid_category(self) -> None:
        valid_categories = {"Untergewicht", "Normalgewicht", "Übergewicht", "Adipositas"}
        sim = Simulator()
        for _ in range(50):
            result = sim.gewicht()
            assert result["klasse"] in valid_categories

    def test_gewicht_plausible_range(self) -> None:
        sim = Simulator(geschlecht="männlich", groesse_cm=180, alter=40)
        for _ in range(50):
            result = sim.gewicht()
            assert 30 <= result["gewicht"] <= 250

    def test_child_uses_different_bmi_ranges(self) -> None:
        child_sim = Simulator(geschlecht="weiblich", groesse_cm=150, alter=14)
        result = child_sim.gewicht()
        assert result["bmi"] >= 10
        assert result["bmi"] <= 45

    def test_adult_bmi_range(self) -> None:
        sim = Simulator(alter=30)
        for _ in range(50):
            result = sim.gewicht()
            assert 12 <= result["bmi"] <= 55


class TestSimulatorInit:
    def test_default_parameters(self) -> None:
        sim = Simulator()
        assert sim.geschlecht == "divers"
        assert sim.groesse_cm == 173
        assert sim.alter == 18

    def test_custom_parameters(self) -> None:
        sim = Simulator(geschlecht="Männlich", groesse_cm=190, alter=65)
        assert sim.geschlecht == "männlich"
        assert sim.groesse_cm == 190
        assert sim.alter == 65

    def test_geschlecht_normalized_to_lower(self) -> None:
        sim = Simulator(geschlecht="WEIBLICH")
        assert sim.geschlecht == "weiblich"
