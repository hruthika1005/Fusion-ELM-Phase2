from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..models import LeaveCancellationRequest, LeaveExtensionRequest, LeaveRequest, LeaveResumption
from ..services.leave_requests import (
    approve_leave_request,
    create_leave_request,
    decide_leave_cancellation,
    decide_leave_extension,
    decide_leave_resumption,
    reject_leave_request,
    replace_substitute,
    respond_to_substitute_request,
    request_leave_cancellation,
    request_leave_extension,
    submit_leave_resumption,
    withdraw_leave_request,
)
from .serializers import LeaveRequestSerializer


MODULE = HasModuleGrant("elm")

P_VIEW_SELF = "elm.leave_request.view_self"
P_VIEW = "elm.leave_request.view"
P_CREATE = "elm.leave_request.create"
P_WITHDRAW = "elm.leave_request.withdraw"
P_APPROVE = "elm.leave_request.approve"
P_RESPOND_SUBSTITUTE = "elm.leave_request.respond_substitute"
P_REPLACE_SUBSTITUTE = "elm.leave_request.replace_substitute"
P_CANCEL = "elm.leave_request.cancel"
P_EXTEND = "elm.leave_request.extend"
P_RESUME = "elm.leave_request.resume"


class _LeaveRequestScoped:
    def _actor(self):
        return getattr(self.request, "principal", None)

    def get_queryset(self):
        actor = self._actor()
        if actor is None or getattr(actor, "user_id", None) is None:
            return LeaveRequest.objects.none()

        if actor.has_permission(P_VIEW):
            return LeaveRequest.objects.all()

        if actor.has_permission(P_VIEW_SELF):
            return LeaveRequest.objects.filter(user_id=actor.user_id)

        return LeaveRequest.objects.none()


class LeaveRequestListView(_LeaveRequestScoped, generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permission() for permission in (MODULE, HasPermission(P_CREATE))]
        return [permission() for permission in (
            MODULE,
            HasPermission(P_VIEW_SELF, P_VIEW),
        )]

    def perform_create(self, serializer):
        actor = self._actor()
        if actor is None or getattr(actor, "user_id", None) is None:
            raise PermissionDenied("A signed-in employee is required.")
        if getattr(actor, "kind", None) not in {"faculty", "staff"}:
            raise PermissionDenied("Only faculty and staff can submit leave requests.")

        try:
            leave_request = create_leave_request(
                user_id=actor.user_id,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or exc.messages
            raise ValidationError(detail) from exc
        serializer.instance = leave_request


class LeaveRequestDetailView(
    _LeaveRequestScoped,
    generics.RetrieveUpdateAPIView,
):
    serializer_class = LeaveRequestSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [permission() for permission in (
                MODULE,
                HasPermission(P_WITHDRAW, P_APPROVE),
            )]
        return [permission() for permission in (
            MODULE,
            HasPermission(P_VIEW_SELF, P_VIEW),
        )]

    def perform_update(self, serializer):
        raise PermissionDenied(
            "Direct leave-request updates are disabled. "
            "Use an authorised workflow action."
        )


class LeaveRequestWithdrawView(_LeaveRequestScoped, APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk):
        leave_request = self.get_queryset().filter(pk=pk).first()
        if leave_request is None:
            raise PermissionDenied("You cannot withdraw this leave request.")
        if leave_request.user_id != request.principal.user_id:
            raise PermissionDenied("Only the applicant may withdraw a leave request.")

        try:
            leave_request = withdraw_leave_request(leave_request.pk)
        except ValueError as exc:
            raise ValidationError({"status": str(exc)}) from exc

        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_200_OK)


class LeaveRequestDecisionView(_LeaveRequestScoped, APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk):
        leave_request = self.get_queryset().filter(pk=pk).first()
        if leave_request is None:
            raise PermissionDenied("You cannot decide this leave request.")

        action = request.data.get("action")
        if action not in {"approve", "reject"}:
            raise ValidationError({
                "action": "Action must be either 'approve' or 'reject'."
            })

        try:
            if action == "approve":
                leave_request = approve_leave_request(leave_request.pk)
            else:
                leave_request = reject_leave_request(leave_request.pk)
        except ValueError as exc:
            raise ValidationError({"status": str(exc)}) from exc

        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_200_OK)


class LeaveRequestSubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_RESPOND_SUBSTITUTE)]

    def post(self, request, pk):
        actor = getattr(request, "principal", None)
        if actor is None or getattr(actor, "kind", None) not in {"faculty", "staff"}:
            raise PermissionDenied("Only an employee may respond as a substitute.")

        action = request.data.get("action")
        if action not in {"accept", "decline"}:
            raise ValidationError({
                "action": "Action must be either 'accept' or 'decline'."
            })

        try:
            leave_request = respond_to_substitute_request(pk, actor.user_id, action)
        except (LeaveRequest.DoesNotExist, ValueError) as exc:
            raise PermissionDenied("You cannot respond to this substitute request.") from exc

        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_200_OK)


class LeaveRequestReplaceSubstituteView(_LeaveRequestScoped, APIView):
    permission_classes = [MODULE, HasPermission(P_REPLACE_SUBSTITUTE)]

    def post(self, request, pk):
        actor = self._actor()
        leave_request = self.get_queryset().filter(pk=pk).first()
        if leave_request is None or leave_request.user_id != actor.user_id:
            raise PermissionDenied("Only the applicant may replace a substitute.")

        substitute_user_id = request.data.get("substitute_user_id")
        if substitute_user_id is None:
            raise ValidationError({"substitute_user_id": "This field is required."})

        try:
            leave_request = replace_substitute(
                leave_request.pk,
                actor.user_id,
                int(substitute_user_id),
            )
        except (DjangoValidationError, ValueError) as exc:
            detail = getattr(exc, "message_dict", None) or {"substitute_user_id": str(exc)}
            raise ValidationError(detail) from exc

        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_200_OK)


class LeaveRequestCancellationView(_LeaveRequestScoped, APIView):
    permission_classes = [MODULE, HasPermission(P_CANCEL)]

    def post(self, request, pk):
        actor = self._actor()
        leave_request = self.get_queryset().filter(pk=pk).first()
        if leave_request is None or leave_request.user_id != actor.user_id:
            raise PermissionDenied("Only the applicant may request cancellation.")

        try:
            cancellation = request_leave_cancellation(
                leave_request.pk,
                actor.user_id,
                request.data.get("reason", ""),
            )
        except (DjangoValidationError, ValueError) as exc:
            detail = getattr(exc, "message_dict", None) or {"reason": str(exc)}
            raise ValidationError(detail) from exc

        return Response({
            "id": cancellation.pk,
            "leave_request_id": cancellation.leave_request_id,
            "status": cancellation.status,
        }, status=status.HTTP_201_CREATED)


class LeaveCancellationDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk):
        action = request.data.get("action")
        try:
            cancellation = decide_leave_cancellation(pk, action)
        except (LeaveCancellationRequest.DoesNotExist, ValueError) as exc:
            raise ValidationError({"action": str(exc)}) from exc

        return Response({
            "id": cancellation.pk,
            "leave_request_id": cancellation.leave_request_id,
            "status": cancellation.status,
        }, status=status.HTTP_200_OK)


class LeaveRequestExtensionView(_LeaveRequestScoped, APIView):
    permission_classes = [MODULE, HasPermission(P_EXTEND)]

    def post(self, request, pk):
        actor = self._actor()
        leave_request = self.get_queryset().filter(pk=pk).first()
        if leave_request is None or leave_request.user_id != actor.user_id:
            raise PermissionDenied("Only the applicant may request an extension.")
        try:
            extension = request_leave_extension(
                leave_request.pk, actor.user_id,
                request.data.get("requested_end_date"), request.data.get("reason", ""),
            )
        except (DjangoValidationError, ValueError) as exc:
            detail = getattr(exc, "message_dict", None) or {"requested_end_date": str(exc)}
            raise ValidationError(detail) from exc
        return Response({"id": extension.pk, "status": extension.status}, status=status.HTTP_201_CREATED)


class LeaveExtensionDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk):
        try:
            extension = decide_leave_extension(pk, request.data.get("action"))
        except (LeaveExtensionRequest.DoesNotExist, ValueError) as exc:
            raise ValidationError({"action": str(exc)}) from exc
        return Response({"id": extension.pk, "status": extension.status}, status=status.HTTP_200_OK)


class LeaveRequestResumptionView(_LeaveRequestScoped, APIView):
    permission_classes = [MODULE, HasPermission(P_RESUME)]

    def post(self, request, pk):
        actor = self._actor()
        leave_request = self.get_queryset().filter(pk=pk).first()
        if leave_request is None or leave_request.user_id != actor.user_id:
            raise PermissionDenied("Only the applicant may submit resumption.")
        try:
            resumption = submit_leave_resumption(
                leave_request.pk, actor.user_id,
                request.data.get("actual_resumption_date"), request.data.get("details", ""),
            )
        except (DjangoValidationError, ValueError) as exc:
            detail = getattr(exc, "message_dict", None) or {"actual_resumption_date": str(exc)}
            raise ValidationError(detail) from exc
        return Response({"id": resumption.pk, "status": resumption.status}, status=status.HTTP_201_CREATED)


class LeaveResumptionDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk):
        try:
            resumption = decide_leave_resumption(pk, request.data.get("action"))
        except (LeaveResumption.DoesNotExist, ValueError) as exc:
            raise ValidationError({"action": str(exc)}) from exc
        return Response({"id": resumption.pk, "status": resumption.status}, status=status.HTTP_200_OK)
