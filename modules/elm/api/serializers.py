
from rest_framework import serializers

from ..models import LEAVE_TYPES, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "half_day",
            "half_day_session",
            "reason",
            "substitute_user_id",
            "substitute_status",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "status",
            "substitute_status",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date must be on or after start date."
            })

        leave_type = attrs.get("leave_type", getattr(self.instance, "leave_type", None))
        if leave_type not in LEAVE_TYPES:
            raise serializers.ValidationError({
                "leave_type": "Unsupported leave type."
            })

        return attrs
