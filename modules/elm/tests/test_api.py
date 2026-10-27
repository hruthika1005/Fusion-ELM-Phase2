import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.elm.models import LeaveRequest
from modules.elm.services.leave_requests import (
    create_leave_request,
    respond_to_substitute_request,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id=1001, permissions=(), kind="faculty"):
    stub_iam(make_session(
        user_id=user_id,
        modules=("elm",),
        permissions=permissions,
        kind=kind,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token user-{user_id}")
    return client


def _employee(user_id):
    return UserRef.objects.create(
        user_id=user_id,
        username=f"employee{user_id}",
        display_name=f"Employee {user_id}",
        kind="staff",
    )


def test_employee_can_create_their_own_leave_request(stub_iam):
    client = _client(
        stub_iam,
        permissions=("elm.leave_request.create",),
    )

    response = client.post(
        "/api/v1/elm/leave-requests/",
        {
            "leave_type": "CL",
            "start_date": "2023-10-01",
            "end_date": "2023-10-01",
            "half_day": True,
            "half_day_session": "first",
            "reason": "Medical appointment",
        },
        format="json",
    )

    assert response.status_code == 201
    request = LeaveRequest.objects.get()
    assert request.user_id == 1001
    assert request.status == "pending"
    assert request.half_day_session == "first"


def test_student_cannot_create_a_leave_request(stub_iam):
    client = _client(
        stub_iam,
        kind="student",
        permissions=("elm.leave_request.create",),
    )

    response = client.post(
        "/api/v1/elm/leave-requests/",
        {
            "leave_type": "CL",
            "start_date": "2023-10-01",
            "end_date": "2023-10-01",
            "half_day": False,
            "reason": "Not an employee",
        },
        format="json",
    )

    assert response.status_code == 403
    assert LeaveRequest.objects.count() == 0


def test_create_rejects_an_active_overlap(stub_iam):
    create_leave_request(
        user_id=1001,
        leave_type="EL",
        start_date=datetime.date(2023, 10, 1),
        end_date=datetime.date(2023, 10, 3),
        half_day=False,
        reason="Existing leave",
    )
    client = _client(
        stub_iam,
        permissions=("elm.leave_request.create",),
    )

    response = client.post(
        "/api/v1/elm/leave-requests/",
        {
            "leave_type": "CL",
            "start_date": "2023-10-02",
            "end_date": "2023-10-02",
            "half_day": False,
            "reason": "Overlap",
        },
        format="json",
    )

    assert response.status_code == 400
    details = response.json()["error"]["details"]
    assert any(item["field"] == "start_date" for item in details)


def test_only_the_applicant_can_withdraw_a_pending_request(stub_iam):
    request = create_leave_request(
        user_id=1001,
        leave_type="CL",
        start_date=datetime.date(2023, 10, 1),
        end_date=datetime.date(2023, 10, 1),
        half_day=False,
        reason="Personal leave",
    )
    owner = _client(
        stub_iam,
        user_id=1001,
        permissions=(
            "elm.leave_request.view_self",
            "elm.leave_request.withdraw",
        ),
    )

    response = owner.post(f"/api/v1/elm/leave-requests/{request.pk}/withdraw/")

    assert response.status_code == 200
    request.refresh_from_db()
    assert request.status == "withdrawn"


def test_withdrawal_is_not_available_after_approval(stub_iam):
    request = LeaveRequest.objects.create(
        user_id=1001,
        leave_type="CL",
        start_date=datetime.date(2023, 10, 1),
        end_date=datetime.date(2023, 10, 1),
        half_day=False,
        reason="Already approved",
        status="approved",
    )
    client = _client(
        stub_iam,
        user_id=1001,
        permissions=(
            "elm.leave_request.view_self",
            "elm.leave_request.withdraw",
        ),
    )

    response = client.post(f"/api/v1/elm/leave-requests/{request.pk}/withdraw/")

    assert response.status_code == 400
    request.refresh_from_db()
    assert request.status == "approved"


def test_authorized_reviewer_can_approve_a_pending_request(stub_iam):
    request = create_leave_request(
        user_id=1001,
        leave_type="CL",
        start_date=datetime.date(2023, 10, 1),
        end_date=datetime.date(2023, 10, 1),
        half_day=False,
        reason="Personal leave",
    )
    reviewer = _client(
        stub_iam,
        user_id=2001,
        kind="staff",
        permissions=(
            "elm.leave_request.view",
            "elm.leave_request.approve",
        ),
    )

    response = reviewer.post(
        f"/api/v1/elm/leave-requests/{request.pk}/decision/",
        {"action": "approve"},
        format="json",
    )

    assert response.status_code == 200
    request.refresh_from_db()
    assert request.status == "approved"


def test_decision_endpoint_rejects_unknown_action(stub_iam):
    request = create_leave_request(
        user_id=1001,
        leave_type="CL",
        start_date=datetime.date(2023, 10, 1),
        end_date=datetime.date(2023, 10, 1),
        half_day=False,
        reason="Personal leave",
    )
    reviewer = _client(
        stub_iam,
        user_id=2001,
        kind="staff",
        permissions=(
            "elm.leave_request.view",
            "elm.leave_request.approve",
        ),
    )

    response = reviewer.post(
        f"/api/v1/elm/leave-requests/{request.pk}/decision/",
        {"action": "cancel"},
        format="json",
    )

    assert response.status_code == 400
    request.refresh_from_db()
    assert request.status == "pending"


def test_substitute_acceptance_releases_request_for_review(stub_iam):
    _employee(2001)
    applicant = _client(
        stub_iam,
        user_id=1001,
        permissions=("elm.leave_request.create",),
    )

    response = applicant.post(
        "/api/v1/elm/leave-requests/",
        {
            "leave_type": "EL",
            "start_date": "2023-10-01",
            "end_date": "2023-10-03",
            "half_day": False,
            "reason": "Conference attendance",
            "substitute_user_id": 2001,
        },
        format="json",
    )

    assert response.status_code == 201
    request = LeaveRequest.objects.get()
    assert request.status == "awaiting_substitute"
    assert request.substitute_status == "pending"

    substitute = _client(
        stub_iam,
        user_id=2001,
        kind="staff",
        permissions=("elm.leave_request.respond_substitute",),
    )
    response = substitute.post(
        f"/api/v1/elm/leave-requests/{request.pk}/substitute-response/",
        {"action": "accept"},
        format="json",
    )

    assert response.status_code == 200
    request.refresh_from_db()
    assert request.status == "pending"
    assert request.substitute_status == "accepted"


def test_declined_substitute_can_be_replaced_by_the_applicant(stub_iam):
    _employee(2001)
    _employee(2002)
    request = create_leave_request(
        user_id=1001,
        leave_type="EL",
        start_date=datetime.date(2023, 10, 1),
        end_date=datetime.date(2023, 10, 3),
        half_day=False,
        reason="Conference attendance",
        substitute_user_id=2001,
    )
    respond_to_substitute_request(request.pk, 2001, "decline")

    applicant = _client(
        stub_iam,
        user_id=1001,
        permissions=(
            "elm.leave_request.view_self",
            "elm.leave_request.replace_substitute",
        ),
    )
    response = applicant.post(
        f"/api/v1/elm/leave-requests/{request.pk}/replace-substitute/",
        {"substitute_user_id": 2002},
        format="json",
    )

    assert response.status_code == 200
    request.refresh_from_db()
    assert request.substitute_user_id == 2002
    assert request.status == "awaiting_substitute"
    assert request.substitute_status == "pending"


def test_approved_future_leave_can_be_cancelled_after_final_decision(stub_iam):
    start_date = datetime.date.today() + datetime.timedelta(days=10)
    request = LeaveRequest.objects.create(
        user_id=1001,
        leave_type="EL",
        start_date=start_date,
        end_date=start_date + datetime.timedelta(days=2),
        half_day=False,
        reason="Approved leave",
        status="approved",
    )
    applicant = _client(
        stub_iam,
        user_id=1001,
        permissions=("elm.leave_request.view_self", "elm.leave_request.cancel"),
    )
    response = applicant.post(
        f"/api/v1/elm/leave-requests/{request.pk}/cancellation/",
        {"reason": "Travel plans changed"},
        format="json",
    )

    assert response.status_code == 201
    cancellation_id = response.json()["id"]
    reviewer = _client(
        stub_iam,
        user_id=2001,
        kind="staff",
        permissions=("elm.leave_request.approve",),
    )
    response = reviewer.post(
        f"/api/v1/elm/leave-cancellations/{cancellation_id}/decision/",
        {"action": "approve"},
        format="json",
    )

    assert response.status_code == 200
    request.refresh_from_db()
    assert request.status == "cancelled"


def test_cancellation_is_rejected_after_leave_begins(stub_iam):
    start_date = datetime.date.today()
    request = LeaveRequest.objects.create(
        user_id=1001,
        leave_type="EL",
        start_date=start_date,
        end_date=start_date,
        half_day=False,
        reason="Current leave",
        status="approved",
    )
    applicant = _client(
        stub_iam,
        user_id=1001,
        permissions=("elm.leave_request.view_self", "elm.leave_request.cancel"),
    )

    response = applicant.post(
        f"/api/v1/elm/leave-requests/{request.pk}/cancellation/",
        {"reason": "Too late"},
        format="json",
    )

    assert response.status_code == 400


def test_ongoing_el_extension_can_be_requested_and_approved(stub_iam):
    today = datetime.date.today()
    request = LeaveRequest.objects.create(
        user_id=1001, leave_type="EL", start_date=today - datetime.timedelta(days=1),
        end_date=today + datetime.timedelta(days=1), half_day=False,
        reason="Ongoing leave", status="approved",
    )
    applicant = _client(stub_iam, user_id=1001, permissions=("elm.leave_request.view_self", "elm.leave_request.extend"))
    response = applicant.post(
        f"/api/v1/elm/leave-requests/{request.pk}/extension/",
        {"requested_end_date": str(today + datetime.timedelta(days=3)), "reason": "Recovery requires more time"},
        format="json",
    )
    assert response.status_code == 201
    reviewer = _client(stub_iam, user_id=2001, kind="staff", permissions=("elm.leave_request.approve",))
    response = reviewer.post(
        f"/api/v1/elm/leave-extensions/{response.json()['id']}/decision/",
        {"action": "approve"}, format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_resumption_can_be_submitted_and_reviewed(stub_iam):
    today = datetime.date.today()
    request = LeaveRequest.objects.create(
        user_id=1001, leave_type="EL", start_date=today - datetime.timedelta(days=5),
        end_date=today, half_day=False, reason="Approved leave", status="approved",
    )
    applicant = _client(stub_iam, user_id=1001, permissions=("elm.leave_request.view_self", "elm.leave_request.resume"))
    response = applicant.post(
        f"/api/v1/elm/leave-requests/{request.pk}/resumption/",
        {"actual_resumption_date": str(today), "details": "Returned to duty"}, format="json",
    )
    assert response.status_code == 201
    reviewer = _client(stub_iam, user_id=2001, kind="staff", permissions=("elm.leave_request.approve",))
    response = reviewer.post(
        f"/api/v1/elm/leave-resumptions/{response.json()['id']}/decision/",
        {"action": "approve"}, format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
