import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from modules.elm.models import LeaveRequest
from modules.elm.models import Holiday, HolidayCalendar
from modules.elm.services.leave_requests import create_leave_request


class LeaveRequestDateValidationTests(TestCase):
    def _request(self, **overrides):
        values = {
            "user_id": 1,
            "leave_type": "CL",
            "start_date": datetime.date(2023, 10, 1),
            "end_date": datetime.date(2023, 10, 1),
            "half_day": False,
            "half_day_session": "",
            "reason": "Date validation test",
            "status": "pending",
        }
        values.update(overrides)
        return LeaveRequest(**values)

    def test_end_date_before_start_date_is_rejected(self):
        leave_request = LeaveRequest(
            user_id=1,
            leave_type="CL",
            start_date=datetime.date(2023, 10, 1),
            end_date=datetime.date(2023, 9, 30),
            half_day=False,
            reason="Date validation test",
        )

        with self.assertRaises(ValidationError):
            leave_request.full_clean()

    def test_create_service_rejects_invalid_date_range(self):
        with self.assertRaises(ValidationError):
            create_leave_request(
                user_id=1,
                leave_type="CL",
                start_date=datetime.date(2023, 10, 1),
                end_date=datetime.date(2023, 9, 30),
                half_day=False,
                reason="Invalid date range",
            )

    def test_create_service_stores_required_submission_fields(self):
        leave_request = create_leave_request(
            user_id=1,
            leave_type="CL",
            start_date=datetime.date(2023, 10, 1),
            end_date=datetime.date(2023, 10, 1),
            half_day=False,
            reason="Conference attendance",
        )

        self.assertEqual(leave_request.reason, "Conference attendance")
        self.assertEqual(leave_request.half_day_session, "")

    def test_rh_requires_a_published_restricted_holiday(self):
        date = datetime.date(2023, 10, 2)
        with self.assertRaises(ValidationError):
            self._request(leave_type="RH", start_date=date, end_date=date).full_clean()

        calendar = HolidayCalendar.objects.create(year=2023, is_published=True)
        Holiday.objects.create(calendar=calendar, date=date, name="Restricted holiday", is_restricted=True)
        self._request(leave_type="RH", start_date=date, end_date=date).full_clean()
