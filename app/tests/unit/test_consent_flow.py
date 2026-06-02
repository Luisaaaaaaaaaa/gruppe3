"""Unit-Tests fuer Consent-Flow und Rollenerklärung."""

from app.dialogue.consent_flow import (
    CONSENT_ACCEPTED,
    CONSENT_DECLINED,
    CONSENT_QUESTION,
    ROLE_EXPLANATION,
    is_consent_given,
)


class TestIsConsentGiven:
    def test_ja_accepted(self) -> None:
        assert is_consent_given("ja") is True

    def test_j_accepted(self) -> None:
        assert is_consent_given("j") is True

    def test_yes_accepted(self) -> None:
        assert is_consent_given("yes") is True

    def test_nein_declined(self) -> None:
        assert is_consent_given("nein") is False

    def test_n_declined(self) -> None:
        assert is_consent_given("n") is False

    def test_no_declined(self) -> None:
        assert is_consent_given("no") is False

    def test_case_insensitive(self) -> None:
        assert is_consent_given("JA") is True
        assert is_consent_given("NEIN") is False

    def test_whitespace_handled(self) -> None:
        assert is_consent_given("  ja  ") is True

    def test_invalid_returns_none(self) -> None:
        assert is_consent_given("vielleicht") is None
        assert is_consent_given("") is None
        assert is_consent_given("123") is None


class TestConsentTexts:
    def test_role_explanation_mentions_assistenzsystem(self) -> None:
        assert "Assistenz" in ROLE_EXPLANATION or "assistenz" in ROLE_EXPLANATION.lower()

    def test_role_explanation_no_diagnosis(self) -> None:
        text = ROLE_EXPLANATION.lower()
        assert "keine diagnose" in text or "stellt keine diagnose" in text or "kein" in text

    def test_consent_question_not_empty(self) -> None:
        assert len(CONSENT_QUESTION) > 10

    def test_consent_accepted_not_empty(self) -> None:
        assert len(CONSENT_ACCEPTED) > 5

    def test_consent_declined_not_empty(self) -> None:
        assert len(CONSENT_DECLINED) > 5
