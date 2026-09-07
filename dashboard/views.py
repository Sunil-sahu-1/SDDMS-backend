from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, UserVerification
from audit.models import AuditLog
from cases.models import Case
from complaints.models import Complaint
from documents.models import Document
from evidence.models import Evidence
from investigations.models import Investigation
from legal.models import CourtHearing, LegalReview

from .permissions import IsAdminUserRole


class AdminDashboardView(APIView):

    permission_classes = [IsAdminUserRole]

    def get(self, request):

        case_status = dict(
            Case.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        investigation_status = dict(
            Investigation.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        complaint_status = dict(
            Complaint.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        legal_review_status = dict(
            LegalReview.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        hearing_status = dict(
            CourtHearing.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        verification_status = dict(
            UserVerification.objects.values_list("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        user_roles = dict(
            User.objects.values_list("role")
            .annotate(count=Count("id"))
            .values_list("role", "count")
        )

        audit_actions = dict(
            AuditLog.objects.values_list("action")
            .annotate(count=Count("id"))
            .values_list("action", "count")
        )

        recent_activity = []

        for log in AuditLog.objects.select_related(
            "user",
            "case",
            "document",
        ).order_by("-created_at")[:10]:

            recent_activity.append({
                "id": log.id,
                "action": log.action,
                "description": log.description,
                "username": log.user.username,
                "case_id": log.case_id,
                "document_id": log.document_id,
                "created_at": log.created_at,
            })

        return Response({
            "success": True,

            "users": {
                "total": User.objects.count(),
                "active": User.objects.filter(
                    is_active=True
                ).count(),
                "inactive": User.objects.filter(
                    is_active=False
                ).count(),
                "by_role": user_roles,
            },

            "verification": {
                "total": UserVerification.objects.count(),
                "pending": UserVerification.objects.filter(
                    status=UserVerification.Status.PENDING
                ).count(),
                "verified": UserVerification.objects.filter(
                    status=UserVerification.Status.VERIFIED
                ).count(),
                "rejected": UserVerification.objects.filter(
                    status=UserVerification.Status.REJECTED
                ).count(),
                "by_status": verification_status,
            },

            "cases": {
                "total": Case.objects.count(),
                "by_status": case_status,
            },

            "investigations": {
                "total": Investigation.objects.count(),
                "by_status": investigation_status,
            },

            "complaints": {
                "total": Complaint.objects.count(),
                "by_status": complaint_status,
            },

            "documents": {
                "total": Document.objects.count(),
                "active": Document.objects.filter(
                    is_archived=False
                ).count(),
                "archived": Document.objects.filter(
                    is_archived=True
                ).count(),
            },

            "evidence": {
                "total": Evidence.objects.count(),
                "active": Evidence.objects.filter(
                    is_archived=False
                ).count(),
                "archived": Evidence.objects.filter(
                    is_archived=True
                ).count(),
            },

            "legal": {
                "total_reviews": LegalReview.objects.count(),
                "reviews_by_status": legal_review_status,
                "total_hearings": CourtHearing.objects.count(),
                "hearings_by_status": hearing_status,
            },

            "security": {
                "total_audit_logs": AuditLog.objects.count(),
                "access_denied": AuditLog.objects.filter(
                    action=AuditLog.Action.ACCESS_DENIED
                ).count(),
                "logins": AuditLog.objects.filter(
                    action=AuditLog.Action.LOGIN
                ).count(),
                "logouts": AuditLog.objects.filter(
                    action=AuditLog.Action.LOGOUT
                ).count(),
                "by_action": audit_actions,
            },

            "recent_activity": recent_activity,
        })
