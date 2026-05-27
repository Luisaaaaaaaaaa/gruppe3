from enum import Enum


class DialogueState(Enum):
    EXPLAIN_ROLE = "explain_role"
    REQUEST_CONSENT = "request_consent"
    ANAMNESIS = "anamnesis"
    VITAL_PARAMETERS = "vital_parameters"
    RED_FLAG_CHECK = "red_flag_check"
    ESCALATION = "escalation"
    SUMMARY = "summary"
    HANDOVER = "handover"
    END = "end"


_TRANSITIONS: dict[DialogueState, DialogueState | None] = {
    DialogueState.EXPLAIN_ROLE: DialogueState.REQUEST_CONSENT,
    DialogueState.REQUEST_CONSENT: DialogueState.ANAMNESIS,
    DialogueState.ANAMNESIS: DialogueState.VITAL_PARAMETERS,
    DialogueState.VITAL_PARAMETERS: DialogueState.RED_FLAG_CHECK,
    DialogueState.RED_FLAG_CHECK: DialogueState.SUMMARY,
    DialogueState.ESCALATION: DialogueState.END,
    DialogueState.SUMMARY: DialogueState.HANDOVER,
    DialogueState.HANDOVER: DialogueState.END,
    DialogueState.END: None,
}


class StateMachine:
    def __init__(self) -> None:
        self._state = DialogueState.EXPLAIN_ROLE

    @property
    def state(self) -> DialogueState:
        return self._state

    def advance(self) -> DialogueState | None:
        next_state = _TRANSITIONS.get(self._state)
        if next_state is None:
            return None
        self._state = next_state
        return self._state

    def jump_to(self, target: DialogueState) -> None:
        self._state = target
