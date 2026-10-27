from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


HALF_DAY_SESSION_CHOICES = (
    ("first", "First half"),
    ("second", "Second half"),
)

SUBSTITUTE_STATUS_CHOICES = (
    ("not_required", "Not required"),
    ("pending", "Awaiting response"),
    ("accepted", "Accepted"),
    ("declined", "Declined"),
)

LEAVE_TYPES = ("CL", "RH", "SCL", "EL", "COL", "VL")
ACTIVE_LEAVE_STATUSES = ("awaiting_substitute", "pending", "approved")


class LeaveRequest(models.Model):
    user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    reason = models.TextField()
    half_day_session = models.CharField(
        max_length=6,
        choices=HALF_DAY_SESSION_CHOICES,
        blank=True,
        default="",
    )
    substitute_user_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    substitute_status = models.CharField(
        max_length=20,
        choices=SUBSTITUTE_STATUS_CHOICES,
        default="not_required",
    )
    status = models.CharField(max_length=50, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}
        if self.leave_type not in LEAVE_TYPES:
            errors["leave_type"] = (
                "Leave type must be one of: " + ", ".join(LEAVE_TYPES) + "."
            )

        if not self.reason or not self.reason.strip():
            errors["reason"] = "A purpose or reason is required."

        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date must be on or after start date."

        if self.half_day and self.start_date != self.end_date:
            errors["end_date"] = "Half-day leave must start and end on the same date."

        if self.half_day and self.half_day_session not in {"first", "second"}:
            errors["half_day_session"] = (
                "Half-day session must be 'first' or 'second'."
            )

        if self.leave_type == "RH" and self.start_date and self.end_date:
            if self.start_date != self.end_date:
                errors["end_date"] = "Restricted Holiday leave must be for one date."
            elif not Holiday.objects.filter(
                calendar__year=self.start_date.year,
                calendar__is_published=True,
                date=self.start_date,
                is_restricted=True,
            ).exists():
                errors["start_date"] = (
                    "RH leave must match a restricted holiday in the published calendar."
                )

        if not self.half_day and self.half_day_session:
            errors["half_day_session"] = (
                "Half-day session must be empty for non-half-day requests."
            )

        if self.substitute_user_id == self.user_id:
            errors["substitute_user_id"] = (
                "The applicant cannot be their own substitute."
            )
        if self.substitute_user_id is None and self.substitute_status != "not_required":
            errors["substitute_status"] = (
                "A substitute status requires a nominated substitute."
            )
        if self.substitute_user_id is not None and self.substitute_status == "not_required":
            errors["substitute_status"] = (
                "A nominated substitute must await or record a response."
            )

        if not errors and self.user_id and self.start_date and self.end_date:
            candidates = LeaveRequest.objects.filter(
                user_id=self.user_id,
                status__in=ACTIVE_LEAVE_STATUSES,
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            )
            if self.pk:
                candidates = candidates.exclude(pk=self.pk)

            for existing in candidates:
                opposite_half_day_cl = (
                    self.leave_type == existing.leave_type == "CL"
                    and self.half_day
                    and existing.half_day
                    and self.start_date == self.end_date == existing.start_date == existing.end_date
                    and self.half_day_session != existing.half_day_session
                )
                if not opposite_half_day_cl:
                    errors["start_date"] = (
                        "This request overlaps an active pending or approved leave request."
                    )
                    break

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"User {self.user_id} - {self.leave_type} - "
            f"{self.start_date} to {self.end_date}"
        )


class LeaveCancellationRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,
        related_name="cancellation_requests",
    )
    requested_by_user_id = models.IntegerField(db_index=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}
        if self.requested_by_user_id != self.leave_request.user_id:
            errors["requested_by_user_id"] = "Only the applicant may request cancellation."
        if self.leave_request.status != "approved":
            errors["leave_request"] = "Only an approved leave request can be cancelled."
        if not self.reason or not self.reason.strip():
            errors["reason"] = "A cancellation reason is required."
        if errors:
            raise ValidationError(errors)


class LeaveExtensionRequest(models.Model):
    STATUS_CHOICES = LeaveCancellationRequest.STATUS_CHOICES

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,
        related_name="extension_requests",
    )
    requested_by_user_id = models.IntegerField(db_index=True)
    requested_end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}
        if self.requested_by_user_id != self.leave_request.user_id:
            errors["requested_by_user_id"] = "Only the applicant may request an extension."
        if self.leave_request.leave_type not in {"EL", "COL", "VL"}:
            errors["leave_request"] = "Only EL, COL, and VL can be extended."
        if self.leave_request.status != "approved":
            errors["leave_request"] = "Only approved leave can be extended."
        if self.requested_end_date <= self.leave_request.end_date:
            errors["requested_end_date"] = "The extension must end after the approved leave."
        if not self.reason or not self.reason.strip():
            errors["reason"] = "An extension reason is required."
        if errors:
            raise ValidationError(errors)


class LeaveResumption(models.Model):
    STATUS_CHOICES = LeaveCancellationRequest.STATUS_CHOICES

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,
        related_name="resumptions",
    )
    submitted_by_user_id = models.IntegerField(db_index=True)
    actual_resumption_date = models.DateField()
    details = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}
        if self.submitted_by_user_id != self.leave_request.user_id:
            errors["submitted_by_user_id"] = "Only the applicant may submit resumption."
        if self.leave_request.leave_type not in {"EL", "COL", "VL"}:
            errors["leave_request"] = "Resumption is supported only for EL, COL, and VL."
        if self.leave_request.status != "approved":
            errors["leave_request"] = "Only approved leave can be resumed."
        if not self.details or not self.details.strip():
            errors["details"] = "Resumption details are required."
        if errors:
            raise ValidationError(errors)


class LeaveBalance(models.Model):
    user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=10, choices=[(code, code) for code in LEAVE_TYPES])
    year = models.PositiveIntegerField()
    entitled_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    carried_forward_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_id", "leave_type", "year"], name="elm_balance_per_year"),
            models.CheckConstraint(condition=Q(entitled_days__gte=0) & Q(carried_forward_days__gte=0) & Q(used_days__gte=0), name="elm_balance_non_negative"),
        ]

    @property
    def available_days(self):
        return self.entitled_days + self.carried_forward_days - self.used_days


class LeaveAccountEntry(models.Model):
    balance = models.ForeignKey(LeaveBalance, on_delete=models.PROTECT, related_name="entries")
    leave_request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="account_entries")
    days = models.DecimalField(max_digits=6, decimal_places=1)
    kind = models.CharField(max_length=20)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class HolidayCalendar(models.Model):
    year = models.PositiveIntegerField(unique=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class Holiday(models.Model):
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=150)
    is_restricted = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="elm_holiday_once_per_calendar_day"),
        ]
