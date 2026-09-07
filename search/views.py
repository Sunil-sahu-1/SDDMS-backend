from accounts.permissions import IsStaffOrAdmin
from rest_framework.response import Response
from rest_framework.views import APIView

from cases.models import Case
from complaints.models import Complaint
from documents.models import Document
from evidence.models import Evidence
from investigations.models import Investigation
from legal.models import CourtHearing, LegalReview


class GlobalSearchView(APIView):

    permission_classes = [IsStaffOrAdmin]
    

    def get(self, request):

        query = request.query_params.get(
            "q",
            ""
        ).strip()

        search_type = request.query_params.get(
            "type",
            "all"
        ).lower()

        if not query:
            return Response({
                "success": True,
                "count": 0,
                "results": [],
                "message": "Search query is required."
            })

        results = []

        if search_type in ("all", "case"):
            results.extend(
                self.search_cases(
                    request,
                    query
                )
            )

        if search_type in ("all", "document"):
            results.extend(
                self.search_documents(
                    request,
                    query
                )
            )

        if search_type in ("all", "evidence"):
            results.extend(
                self.search_evidence(
                    request,
                    query
                )
            )

        if search_type in ("all", "investigation"):
            results.extend(
                self.search_investigations(
                    request,
                    query
                )
            )

        if search_type in ("all", "complaint"):
            results.extend(
                self.search_complaints(
                    request,
                    query
                )
            )

        if search_type in ("all", "legal"):
            results.extend(
                self.search_legal(
                    request,
                    query
                )
            )

        return Response({
            "success": True,
            "query": query,
            "type": search_type,
            "count": len(results),
            "results": results,
        })

    def authorized_cases(self, user):

        if user.role == "ADMIN":
            return Case.objects.all()

        if user.role == "POLICE_OFFICER":
            return Case.objects.filter(
                assigned_officer=user
            )

        if user.role == "INVESTIGATOR":
            return Case.objects.filter(
                assigned_investigator=user
            )

        return Case.objects.none()

    def search_cases(self, request, query):

        cases = self.authorized_cases(
            request.user
        ).filter(
            case_number__icontains=query
        ) | self.authorized_cases(
            request.user
        ).filter(
            fir_number__icontains=query
        ) | self.authorized_cases(
            request.user
        ).filter(
            title__icontains=query
        ) | self.authorized_cases(
            request.user
        ).filter(
            description__icontains=query
        )

        cases = cases.distinct()[:50]

        return [
            {
                "type": "case",
                "id": case.id,
                "case_number": case.case_number,
                "fir_number": case.fir_number,
                "title": case.title,
                "status": case.status,
                "created_at": case.created_at,
            }
            for case in cases
        ]

    def search_documents(self, request, query):

        cases = self.authorized_cases(
            request.user
        )

        documents = Document.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            title__icontains=query
        ) | Document.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            original_filename__icontains=query
        )

        documents = documents.select_related(
            "case"
        ).distinct()[:50]

        return [
            {
                "type": "document",
                "id": document.id,
                "case_id": document.case_id,
                "title": document.title,
                "document_type": document.document_type,
                "original_filename": (
                    document.original_filename
                ),
                "version": document.version,
                "created_at": document.created_at,
            }
            for document in documents
        ]

    def search_evidence(self, request, query):

        cases = self.authorized_cases(
            request.user
        )

        evidence = Evidence.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            evidence_number__icontains=query
        ) | Evidence.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            title__icontains=query
        ) | Evidence.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            description__icontains=query
        ) | Evidence.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            original_filename__icontains=query
        )

        evidence = evidence.select_related(
            "case",
            "current_custodian"
        ).distinct()[:50]

        return [
            {
                "type": "evidence",
                "id": item.id,
                "case_id": item.case_id,
                "evidence_number": (
                    item.evidence_number
                ),
                "title": item.title,
                "evidence_type": (
                    item.evidence_type
                ),
                "current_custodian": (
                    item.current_custodian_id
                ),
                "created_at": item.created_at,
            }
            for item in evidence
        ]

    def search_investigations(
        self,
        request,
        query
    ):

        cases = self.authorized_cases(
            request.user
        )

        investigations = Investigation.objects.filter(
            case__in=cases
        ).filter(
            investigation_number__icontains=query
        ) | Investigation.objects.filter(
            case__in=cases
        ).filter(
            title__icontains=query
        ) | Investigation.objects.filter(
            case__in=cases
        ).filter(
            description__icontains=query
        )

        investigations = investigations.select_related(
            "case",
            "lead_investigator"
        ).distinct()[:50]

        return [
            {
                "type": "investigation",
                "id": item.id,
                "case_id": item.case_id,
                "investigation_number": (
                    item.investigation_number
                ),
                "title": item.title,
                "status": item.status,
                "priority": item.priority,
                "lead_investigator": (
                    item.lead_investigator_id
                ),
                "created_at": item.created_at,
            }
            for item in investigations
        ]

    def search_complaints(
        self,
        request,
        query
    ):

        cases = self.authorized_cases(
            request.user
        )

        complaints = Complaint.objects.filter(
            case__in=cases
        ).filter(
            complaint_number__icontains=query
        ) | Complaint.objects.filter(
            case__in=cases
        ).filter(
            subject__icontains=query
        ) | Complaint.objects.filter(
            case__in=cases
        ).filter(
            description__icontains=query
        )

        complaints = complaints.select_related(
            "case"
        ).distinct()[:50]

        return [
            {
                "type": "complaint",
                "id": item.id,
                "case_id": item.case_id,
                "complaint_number": (
                    item.complaint_number
                ),
                "subject": item.subject,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in complaints
        ]

    def search_legal(
        self,
        request,
        query
    ):

        cases = self.authorized_cases(
            request.user
        )

        results = []

        reviews = LegalReview.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            title__icontains=query
        ) | LegalReview.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            legal_opinion__icontains=query
        ) | LegalReview.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            remarks__icontains=query
        )

        reviews = reviews.select_related(
            "case"
        ).distinct()[:50]

        results.extend([
            {
                "type": "legal_review",
                "id": item.id,
                "case_id": item.case_id,
                "title": item.title,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in reviews
        ])

        hearings = CourtHearing.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            court_name__icontains=query
        ) | CourtHearing.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            hearing_purpose__icontains=query
        ) | CourtHearing.objects.filter(
            case__in=cases,
            is_archived=False
        ).filter(
            outcome__icontains=query
        )

        hearings = hearings.select_related(
            "case"
        ).distinct()[:50]

        results.extend([
            {
                "type": "court_hearing",
                "id": item.id,
                "case_id": item.case_id,
                "court_name": item.court_name,
                "hearing_date": item.hearing_date,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in hearings
        ])

        return results
