from django.utils import timezone

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.utils import create_audit_log

from .models import LegalReview, CourtHearing
from .permissions import LegalAccessPermission
from .serializers import (
    LegalReviewSerializer,
    CourtHearingSerializer,
)


class LegalReviewViewSet(viewsets.ModelViewSet):

    serializer_class = LegalReviewSerializer

    permission_classes = [
        LegalAccessPermission
    ]

    def get_queryset(self):

        user = self.request.user

        if not user.is_authenticated:
            return LegalReview.objects.none()

        if user.role == "ADMIN":
            return LegalReview.objects.filter(
                is_archived=False
            )

        if user.role == "LEGAL_OFFICER":
            return LegalReview.objects.filter(
                legal_officer=user,
                is_archived=False
            )

        return LegalReview.objects.none()

    def perform_create(self, serializer):

        review = serializer.save(
            legal_officer=self.request.user
        )

        create_audit_log(
            request=self.request,
            action="CREATE",
            case=review.case,
            description="Legal review created.",
            metadata={
                "review_id": review.id,
                "title": review.title,
                "status": review.status,
            },
        )

    def perform_update(self, serializer):

        review = serializer.save()

        create_audit_log(
            request=self.request,
            action="UPDATE",
            case=review.case,
            description="Legal review updated.",
            metadata={
                "review_id": review.id,
                "status": review.status,
            },
        )

    def destroy(self, request, *args, **kwargs):

        review = self.get_object()

        review.is_archived = True
        review.status = LegalReview.ReviewStatus.CLOSED

        review.save(
            update_fields=[
                "is_archived",
                "status",
                "updated_at",
            ]
        )

        create_audit_log(
            request=request,
            action="ARCHIVE",
            case=review.case,
            description="Legal review archived.",
            metadata={
                "review_id": review.id,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Legal review archived successfully.",
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(self, request, pk=None):

        review = self.get_object()

        review.status = LegalReview.ReviewStatus.APPROVED
        review.reviewed_at = timezone.now()

        review.save(
            update_fields=[
                "status",
                "reviewed_at",
                "updated_at",
            ]
        )

        create_audit_log(
            request=request,
            action="APPROVE",
            case=review.case,
            description="Legal review approved.",
            metadata={
                "review_id": review.id,
            },
        )

        return Response({
            "success": True,
            "message": "Legal review approved.",
            "data": LegalReviewSerializer(
                review
            ).data,
        })

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    def reject(self, request, pk=None):

        review = self.get_object()

        review.status = LegalReview.ReviewStatus.REJECTED
        review.reviewed_at = timezone.now()

        review.save(
            update_fields=[
                "status",
                "reviewed_at",
                "updated_at",
            ]
        )

        create_audit_log(
            request=request,
            action="REJECT",
            case=review.case,
            description="Legal review rejected.",
            metadata={
                "review_id": review.id,
            },
        )

        return Response({
            "success": True,
            "message": "Legal review rejected.",
            "data": LegalReviewSerializer(
                review
            ).data,
        })


class CourtHearingViewSet(viewsets.ModelViewSet):

    serializer_class = CourtHearingSerializer

    permission_classes = [
        LegalAccessPermission
    ]

    def get_queryset(self):

        user = self.request.user

        if not user.is_authenticated:
            return CourtHearing.objects.none()

        if user.role == "ADMIN":
            return CourtHearing.objects.filter(
                is_archived=False
            )

        if user.role == "LEGAL_OFFICER":
            return CourtHearing.objects.filter(
                legal_officer=user,
                is_archived=False
            )

        return CourtHearing.objects.none()

    def perform_create(self, serializer):

        hearing = serializer.save(
            legal_officer=self.request.user
        )

        create_audit_log(
            request=self.request,
            action="CREATE",
            case=hearing.case,
            description="Court hearing scheduled.",
            metadata={
                "hearing_id": hearing.id,
                "court_name": hearing.court_name,
                "hearing_date": (
                    hearing.hearing_date.isoformat()
                ),
            },
        )

    def perform_update(self, serializer):

        hearing = serializer.save()

        create_audit_log(
            request=self.request,
            action="UPDATE",
            case=hearing.case,
            description="Court hearing updated.",
            metadata={
                "hearing_id": hearing.id,
                "status": hearing.status,
            },
        )

    def destroy(self, request, *args, **kwargs):

        hearing = self.get_object()

        hearing.is_archived = True
        hearing.status = (
            CourtHearing.HearingStatus.CANCELLED
        )

        hearing.save(
            update_fields=[
                "is_archived",
                "status",
                "updated_at",
            ]
        )

        create_audit_log(
            request=request,
            action="ARCHIVE",
            case=hearing.case,
            description="Court hearing archived.",
            metadata={
                "hearing_id": hearing.id,
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Court hearing archived successfully."
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):

        hearing = self.get_object()

        outcome = request.data.get(
            "outcome",
            ""
        ).strip()

        if not outcome:
            raise serializers.ValidationError(
                "Hearing outcome is required."
            )

        hearing.status = (
            CourtHearing.HearingStatus.COMPLETED
        )
        hearing.outcome = outcome

        hearing.save(
            update_fields=[
                "status",
                "outcome",
                "updated_at",
            ]
        )

        create_audit_log(
            request=request,
            action="COMPLETE",
            case=hearing.case,
            description="Court hearing completed.",
            metadata={
                "hearing_id": hearing.id,
                "outcome": outcome,
            },
        )

        return Response({
            "success": True,
            "message": "Court hearing marked as completed.",
            "data": CourtHearingSerializer(
                hearing
            ).data,
        })
