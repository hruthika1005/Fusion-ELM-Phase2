from dataclasses import dataclass


@dataclass(frozen=True)
class LeaveRequestState:
    status: str


class LeaveRequestStateMachine:
    ALLOWED_TRANSITIONS = {
        "awaiting_substitute": {
            "substitute_accept": "pending",
            "substitute_decline": "substitute_declined",
            "withdraw": "withdrawn",
        },
        "substitute_declined": {
            "replace_substitute": "awaiting_substitute",
            "withdraw": "withdrawn",
        },
        "pending": {
            "approve": "approved",
            "reject": "rejected",
            "withdraw": "withdrawn",
            "cancel": "cancelled",
        },
        "approved": {
            "cancel": "cancelled",
        },
    }

    def __init__(self, initial_state: LeaveRequestState):
        self.state = initial_state

    def apply_transition(self, transition: str):
        allowed = self.ALLOWED_TRANSITIONS.get(self.state.status, {})
        new_status = allowed.get(transition)

        if new_status is None:
            raise ValueError(
                f"Transition {transition!r} is not allowed "
                f"from status {self.state.status!r}."
            )

        self.state = LeaveRequestState(status=new_status)
        return self.state
