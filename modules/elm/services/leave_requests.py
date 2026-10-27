from ..domain.state_machine import (
    LeaveRequestState,
    LeaveRequestStateMachine,
)
from ..models import LeaveCancellationRequest, LeaveExtensionRequest, LeaveRequest, LeaveResumption
from django.utils import timezone
from modules.directory.contracts import get_users


def create_leave_request(
    user_id,
    leave_type,
    start_date,
    end_date,
    half_day,
    reason,
    half_day_session="",
    substitute_user_id=None,
):
    substitute_status = "pending" if substitute_user_id is not None else "not_required"
    leave_request = LeaveRequest(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        reason=reason,
        half_day_session=half_day_session,
        substitute_user_id=substitute_user_id,
        substitute_status=substitute_status,
        status="awaiting_substitute" if substitute_user_id is not None else "pending",
    )
    leave_request.full_clean()
    if substitute_user_id is not None:
        _validate_substitute(leave_request)
    leave_request.save()
    return leave_request


def _validate_substitute(leave_request):
    substitute = get_users([leave_request.substitute_user_id]).get(
        leave_request.substitute_user_id
    )
    if (
        substitute is None
        or not substitute.is_active
        or substitute.kind not in {"faculty", "staff"}
    ):
        raise ValidationError({
            "substitute_user_id": "The substitute must be an active employee."
        })

    overlaps = LeaveRequest.objects.filter(
        user_id=leave_request.substitute_user_id,
        status__in=("pending", "approved", "awaiting_substitute"),
        start_date__lte=leave_request.end_date,
        end_date__gte=leave_request.start_date,
    )
    if overlaps.exists():
        raise ValidationError({
            "substitute_user_id": "The substitute has active overlapping leave."
        })


def _transition_leave_request(leave_request_id, transition):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)

    state_machine = LeaveRequestStateMachine(
        LeaveRequestState(status=leave_request.status)
    )
    new_state = state_machine.apply_transition(transition)

    leave_request.status = new_state.status
    leave_request.save(update_fields=["status", "updated_at"])
    return leave_request


def approve_leave_request(leave_request_id):
    return _transition_leave_request(leave_request_id, "approve")


def reject_leave_request(leave_request_id):
    return _transition_leave_request(leave_request_id, "reject")


def withdraw_leave_request(leave_request_id):
    return _transition_leave_request(leave_request_id, "withdraw")


def respond_to_substitute_request(leave_request_id, substitute_user_id, action):
    if action not in {"accept", "decline"}:
        raise ValueError("Substitute response must be 'accept' or 'decline'.")

    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    if leave_request.substitute_user_id != substitute_user_id:
        raise ValueError("Only the nominated substitute may respond.")

    leave_request = _transition_leave_request(
        leave_request_id,
        f"substitute_{action}",
    )
    leave_request.substitute_status = "accepted" if action == "accept" else "declined"
    leave_request.save(update_fields=["substitute_status", "updated_at"])
    return leave_request


def replace_substitute(leave_request_id, applicant_user_id, substitute_user_id):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    if leave_request.user_id != applicant_user_id:
        raise ValueError("Only the applicant may replace a substitute.")

    leave_request.substitute_user_id = substitute_user_id
    leave_request.substitute_status = "pending"
    leave_request.full_clean()
    _validate_substitute(leave_request)
    leave_request = _transition_leave_request(leave_request_id, "replace_substitute")
    leave_request.substitute_user_id = substitute_user_id
    leave_request.substitute_status = "pending"
    leave_request.save(update_fields=["substitute_user_id", "substitute_status", "updated_at"])
    return leave_request


def cancel_leave_request(leave_request_id):
    """Compatibility wrapper for the pre-existing Phase 1 pending cancellation."""
    return _transition_leave_request(leave_request_id, "cancel")


def request_leave_cancellation(leave_request_id, applicant_user_id, reason):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    if leave_request.user_id != applicant_user_id:
        raise ValueError("Only the applicant may request cancellation.")
    if leave_request.start_date <= timezone.localdate():
        raise ValueError("Cancellation is only available before approved leave begins.")

    cancellation = LeaveCancellationRequest(
        leave_request=leave_request,
        requested_by_user_id=applicant_user_id,
        reason=reason,
    )
    cancellation.full_clean()
    if LeaveCancellationRequest.objects.filter(
        leave_request=leave_request,
        status="pending",
    ).exists():
        raise ValueError("A cancellation request is already pending.")
    cancellation.save()
    return cancellation


def decide_leave_cancellation(cancellation_id, action):
    if action not in {"approve", "reject"}:
        raise ValueError("Cancellation decision must be 'approve' or 'reject'.")

    cancellation = LeaveCancellationRequest.objects.select_related(
        "leave_request"
    ).get(id=cancellation_id)
    if cancellation.status != "pending":
        raise ValueError("Only a pending cancellation request can be decided.")

    cancellation.status = "approved" if action == "approve" else "rejected"
    cancellation.save(update_fields=["status", "updated_at"])
    if action == "approve":
        cancel_leave_request(cancellation.leave_request_id)
    return cancellation


def request_leave_extension(leave_request_id, applicant_user_id, requested_end_date, reason):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    if leave_request.user_id != applicant_user_id:
        raise ValueError("Only the applicant may request an extension.")
    today = timezone.localdate()
    if not leave_request.start_date <= today <= leave_request.end_date:
        raise ValueError("An extension can only be requested while leave is ongoing.")

    extension = LeaveExtensionRequest(
        leave_request=leave_request,
        requested_by_user_id=applicant_user_id,
        requested_end_date=requested_end_date,
        reason=reason,
    )
    extension.full_clean()
    if LeaveExtensionRequest.objects.filter(leave_request=leave_request, status="pending").exists():
        raise ValueError("An extension request is already pending.")
    extension.save()
    return extension


def decide_leave_extension(extension_id, action):
    if action not in {"approve", "reject"}:
        raise ValueError("Extension decision must be 'approve' or 'reject'.")
    extension = LeaveExtensionRequest.objects.get(id=extension_id)
    if extension.status != "pending":
        raise ValueError("Only a pending extension request can be decided.")
    extension.status = "approved" if action == "approve" else "rejected"
    extension.save(update_fields=["status", "updated_at"])
    return extension


def submit_leave_resumption(leave_request_id, applicant_user_id, actual_resumption_date, details):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    if leave_request.user_id != applicant_user_id:
        raise ValueError("Only the applicant may submit resumption.")
    resumption = LeaveResumption(
        leave_request=leave_request,
        submitted_by_user_id=applicant_user_id,
        actual_resumption_date=actual_resumption_date,
        details=details,
    )
    resumption.full_clean()
    if LeaveResumption.objects.filter(leave_request=leave_request, status="pending").exists():
        raise ValueError("A resumption submission is already pending.")
    resumption.save()
    return resumption


def decide_leave_resumption(resumption_id, action):
    if action not in {"approve", "reject"}:
        raise ValueError("Resumption decision must be 'approve' or 'reject'.")
    resumption = LeaveResumption.objects.get(id=resumption_id)
    if resumption.status != "pending":
        raise ValueError("Only a pending resumption can be decided.")
    resumption.status = "approved" if action == "approve" else "rejected"
    resumption.save(update_fields=["status", "updated_at"])
    return resumption
