from django.urls import path

from .views import (
    LeaveRequestDecisionView,
    LeaveCancellationDecisionView,
    LeaveExtensionDecisionView,
    LeaveResumptionDecisionView,
    LeaveRequestCancellationView,
    LeaveRequestExtensionView,
    LeaveRequestResumptionView,
    LeaveRequestDetailView,
    LeaveRequestListView,
    LeaveRequestReplaceSubstituteView,
    LeaveRequestSubstituteResponseView,
    LeaveRequestWithdrawView,
)

urlpatterns = [
    path('leave-requests/', LeaveRequestListView.as_view(), name='leave-request-list'),
    path('leave-requests/<int:pk>/', LeaveRequestDetailView.as_view(), name='leave-request-detail'),
    path(
        'leave-requests/<int:pk>/withdraw/',
        LeaveRequestWithdrawView.as_view(),
        name='leave-request-withdraw',
    ),
    path(
        'leave-requests/<int:pk>/decision/',
        LeaveRequestDecisionView.as_view(),
        name='leave-request-decision',
    ),
    path(
        'leave-requests/<int:pk>/substitute-response/',
        LeaveRequestSubstituteResponseView.as_view(),
        name='leave-request-substitute-response',
    ),
    path(
        'leave-requests/<int:pk>/replace-substitute/',
        LeaveRequestReplaceSubstituteView.as_view(),
        name='leave-request-replace-substitute',
    ),
    path(
        'leave-requests/<int:pk>/cancellation/',
        LeaveRequestCancellationView.as_view(),
        name='leave-request-cancellation',
    ),
    path(
        'leave-cancellations/<int:pk>/decision/',
        LeaveCancellationDecisionView.as_view(),
        name='leave-cancellation-decision',
    ),
    path('leave-requests/<int:pk>/extension/', LeaveRequestExtensionView.as_view(), name='leave-request-extension'),
    path('leave-extensions/<int:pk>/decision/', LeaveExtensionDecisionView.as_view(), name='leave-extension-decision'),
    path('leave-requests/<int:pk>/resumption/', LeaveRequestResumptionView.as_view(), name='leave-request-resumption'),
    path('leave-resumptions/<int:pk>/decision/', LeaveResumptionDecisionView.as_view(), name='leave-resumption-decision'),
]
