import pytest

from modules.elm.domain.state_machine import (
    LeaveRequestState,
    LeaveRequestStateMachine,
)


def test_pending_request_can_be_approved():
    machine = LeaveRequestStateMachine(LeaveRequestState("pending"))
    machine.apply_transition("approve")
    assert machine.state.status == "approved"


def test_pending_request_can_be_rejected():
    machine = LeaveRequestStateMachine(LeaveRequestState("pending"))
    machine.apply_transition("reject")
    assert machine.state.status == "rejected"


def test_pending_request_can_be_cancelled():
    machine = LeaveRequestStateMachine(LeaveRequestState("pending"))
    machine.apply_transition("cancel")
    assert machine.state.status == "cancelled"


def test_unknown_transition_does_not_change_state():
    machine = LeaveRequestStateMachine(LeaveRequestState("pending"))
    with pytest.raises(ValueError):
        machine.apply_transition("invalid")
    assert machine.state.status == "pending"


def test_substitute_acceptance_releases_request_for_review():
    machine = LeaveRequestStateMachine(LeaveRequestState("awaiting_substitute"))
    machine.apply_transition("substitute_accept")
    assert machine.state.status == "pending"


def test_declined_substitute_can_be_replaced_but_not_approved():
    machine = LeaveRequestStateMachine(LeaveRequestState("substitute_declined"))
    with pytest.raises(ValueError):
        machine.apply_transition("approve")
    machine.apply_transition("replace_substitute")
    assert machine.state.status == "awaiting_substitute"
