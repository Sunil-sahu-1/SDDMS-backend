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

from .permissions import IsStaffDashboardUser


class AdminDashboardView(APIView):
    """Operational dashboard with role-scoped record metrics."""

    permission_classes = [IsStaffDashboardUser]

    def get(self, request):
        user = request.user
        is_admin = user.role == User.Role.ADMIN

        if is_admin:
            cases_qs = Case.objects.all()
            documents_qs = Document.objects.filter(is_archived=False)
            evidence_qs = Evidence.objects.filter(is_archived=False)
            investigations_qs = Investigation.objects.all()
            complaints_qs = Complaint.objects.all()
            reviews_qs = LegalReview.objects.all()
            hearings_qs = CourtHearing.objects.all()
            audit_qs = AuditLog.objects.all()
        elif user.role == User.Role.POLICE_OFFICER:
            cases_qs = Case.objects.filter(assigned_officer=user)
            documents_qs = Document.objects.filter(
                case__assigned_officer=user,
                is_archived=False,
            )
            evidence_qs = Evidence.objects.filter(
                case__assigned_officer=user,
                is_archived=False,
            )
            investigations_qs = Investigation.objects.filter(
                case__assigned_officer=user,
            )
            complaints_qs = Complaint.objects.filter(
                case__assigned_officer=user,
            )
            reviews_qs = LegalReview.objects.filter(
                case__assigned_officer=user,
            )
            hearings_qs = CourtHearing.objects.filter(
                case__assigned_officer=user,
            )
            audit_qs = AuditLog.objects.filter(user=user)
        elif user.role == User.Role.INVESTIGATOR:
            cases_qs = Case.objects.filter(assigned_investigator=user)
            documents_qs = Document.objects.filter(
                case__assigned_investigator=user,
                is_archived=False,
            )
            evidence_qs = Evidence.objects.filter(
                case__assigned_investigator=user,
                is_archived=False,
            )
            investigations_qs = Investigation.objects.filter(
                case__assigned_investigator=user,
            )
            complaints_qs = Complaint.objects.filter(
                case__assigned_investigator=user,
            )
            reviews_qs = LegalReview.objects.filter(
                case__assigned_investigator=user,
            )
            hearings_qs = CourtHearing.objects.filter(
                case__assigned_investigator=user,
            )
            audit_qs = AuditLog.objects.filter(user=user)
        else:
            cases_qs = Case.objects.filter(assigned_legal_officer=user)
            documents_qs = Document.objects.filter(
                case__assigned_legal_officer=user,
                is_archived=False,
            )
            evidence_qs = Evidence.objects.filter(
                case__assigned_legal_officer=user,
                is_archived=False,
            )
            investigations_qs = Investigation.objects.filter(
                case__assigned_legal_officer=user,
            )
            complaints_qs = Complaint.objects.filter(
                case__assigned_legal_officer=user,
            )
            reviews_qs = LegalReview.objects.filter(
                case__assigned_legal_officer=user,
            )
            hearings_qs = CourtHearing.objects.filter(
                case__assigned_legal_officer=user,
            )
            audit_qs = AuditLog.objects.filter(user=user)

        def status_counts(queryset):
            return dict(
                queryset.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            )

        def role_counts(queryset):
            return dict(
                queryset.values("role")
                .annotate(count=Count("id"))
                .values_list("role", "count")
            )

        case_status = status_counts(cases_qs)
        investigation_status = status_counts(investigations_qs)
        complaint_status = status_counts(complaints_qs)
        legal_review_status = status_counts(reviews_qs)
        hearing_status = status_counts(hearings_qs)

        if is_admin:
            verification_qs = UserVerification.objects.all()
            user_qs = User.objects.all()
        else:
            verification_qs = UserVerification.objects.filter(user=user)
            user_qs = User.objects.filter(pk=user.pk)

        verification_status = status_counts(verification_qs)
        user_roles = role_counts(user_qs)
        audit_actions = dict(
            audit_qs.values("action")
            .annotate(count=Count("id"))
            .values_list("action", "count")
        )

        recent_activity = []
        for log in audit_qs.select_related(
            "user", "case", "document"
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

        evidence_total = evidence_qs.count()
        integrity_verified = evidence_qs.exclude(sha256_hash="").count()
        integrity_percent = (
            round((integrity_verified / evidence_total) * 100)
            if evidence_total
            else 100
        )
        access_denied = audit_qs.filter(
            action=AuditLog.Action.ACCESS_DENIED
        ).count()
        security_score = max(
            90,
            min(100, 98 - min(8, access_denied // 10)),
        )

        return Response({
            "success": True,
            "scope": "ALL" if is_admin else "ASSIGNED",
            "users": {
                "total": user_qs.count(),
                "active": user_qs.filter(is_active=True).count(),
                "inactive": user_qs.filter(is_active=False).count(),
                "by_role": user_roles,
            },
            "verification": {
                "total": verification_qs.count(),
                "pending": verification_qs.filter(
                    status=UserVerification.Status.PENDING
                ).count(),
                "verified": verification_qs.filter(
                    status=UserVerification.Status.VERIFIED
                ).count(),
                "rejected": verification_qs.filter(
                    status=UserVerification.Status.REJECTED
                ).count(),
                "by_status": verification_status,
            },
            "cases": {
                "total": cases_qs.count(),
                "by_status": case_status,
            },
            "investigations": {
                "total": investigations_qs.count(),
                "by_status": investigation_status,
            },
            "complaints": {
                "total": complaints_qs.count(),
                "by_status": complaint_status,
            },
            "documents": {
                "total": documents_qs.count(),
                "active": documents_qs.count(),
                "archived": (
                    Document.objects.filter(
                        case__in=cases_qs,
                        is_archived=True,
                    ).count()
                    if not is_admin
                    else Document.objects.filter(is_archived=True).count()
                ),
            },
            "evidence": {
                "total": evidence_total,
                "active": evidence_total,
                "archived": (
                    Evidence.objects.filter(
                        case__in=cases_qs,
                        is_archived=True,
                    ).count()
                    if not is_admin
                    else Evidence.objects.filter(is_archived=True).count()
                ),
            },
            "legal": {
                "total_reviews": reviews_qs.count(),
                "reviews_by_status": legal_review_status,
                "total_hearings": hearings_qs.count(),
                "hearings_by_status": hearing_status,
            },
            "security": {
                "total_audit_logs": audit_qs.count(),
                "access_denied": access_denied,
                "logins": audit_qs.filter(action=AuditLog.Action.LOGIN).count(),
                "logouts": audit_qs.filter(action=AuditLog.Action.LOGOUT).count(),
                "integrity_verified": integrity_verified,
                "integrity_percent": integrity_percent,
                "security_score": security_score,
                "by_action": audit_actions,
            },
            "recent_activity": recent_activity,
        })
