"""Unit-Tests fuer die Dialogzustandsmaschine."""

from app.dialogue.state_machine import DialogueState, StateMachine


class TestStateMachine:
    def test_initial_state_is_explain_role(self) -> None:
        sm = StateMachine()
        assert sm.state == DialogueState.EXPLAIN_ROLE

    def test_full_transition_sequence(self) -> None:
        sm = StateMachine()
        expected = [
            DialogueState.REQUEST_CONSENT,
            DialogueState.ANAMNESIS,
            DialogueState.VITAL_PARAMETERS,
            DialogueState.RED_FLAG_CHECK,
            DialogueState.SUMMARY,
            DialogueState.HANDOVER,
            DialogueState.END,
        ]
        for expected_state in expected:
            result = sm.advance()
            assert result == expected_state
            assert sm.state == expected_state

    def test_advance_from_end_returns_none(self) -> None:
        sm = StateMachine()
        sm.jump_to(DialogueState.END)
        assert sm.advance() is None
        assert sm.state == DialogueState.END

    def test_jump_to_sets_state(self) -> None:
        sm = StateMachine()
        sm.jump_to(DialogueState.ESCALATION)
        assert sm.state == DialogueState.ESCALATION

    def test_escalation_leads_to_end(self) -> None:
        sm = StateMachine()
        sm.jump_to(DialogueState.ESCALATION)
        result = sm.advance()
        assert result == DialogueState.END

    def test_advance_from_summary_leads_to_handover(self) -> None:
        sm = StateMachine()
        sm.jump_to(DialogueState.SUMMARY)
        result = sm.advance()
        assert result == DialogueState.HANDOVER

    def test_advance_from_handover_leads_to_end(self) -> None:
        sm = StateMachine()
        sm.jump_to(DialogueState.HANDOVER)
        result = sm.advance()
        assert result == DialogueState.END


class TestDialogueStateEnum:
    def test_all_states_have_transitions(self) -> None:
        for state in DialogueState:
            sm = StateMachine()
            sm.jump_to(state)
            sm.advance()

    def test_state_values_are_strings(self) -> None:
        for state in DialogueState:
            assert isinstance(state.value, str)
