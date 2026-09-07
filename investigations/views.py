from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.utils import create_audit_log

from .models import (
    Investigation,
    InvestigationHistory,
    WitnessStatement,
    WitnessStatementMedia,
)

from .permissions import (
    InvestigationPermission,
    WitnessStatementPermission,
)

from .serializers import (
    InvestigationAssignmentSerializer,
    InvestigationSerializer,
    InvestigationStatusSerializer,
    InvestigationTimelineSerializer,
    WitnessStatementMediaSerializer,
    WitnessStatementSerializer,
)


class InvestigationViewSet(viewsets.ModelViewSet):

    serializer_class = InvestigationSerializer

    permission_classes = [
        IsAuthenticated,
        InvestigationPermission,
    ]

    def get_queryset(self):

        user = self.request.user

        if not user.is_authenticated:
            return Investigation.objects.none()

        queryset = (
            Investigation.objects
            .select_related(
                "case",
                "lead_investigator",
                "created_by",
            )
            .prefetch_related(
                "assigned_officers",
            )
        )

        if user.role == "ADMIN":
            return queryset.distinct()

        if user.role == "INVESTIGATOR":
            return queryset.filter(
                Q(lead_investigator=user)
                | Q(assigned_officers=user)
                | Q(case__assigned_investigator=user)
            ).distinct()

        if user.role == "POLICE_OFFICER":
            return queryset.filter(
                Q(assigned_officers=user)
                | Q(case__assigned_officer=user)
            ).distinct()

        return Investigation.objects.none()

    def perform_create(self, serializer):

        investigation = serializer.save(
            created_by=self.request.user
        )

        InvestigationHistory.objects.create(
            investigation=investigation,
            changed_by=self.request.user,
            old_status="",
            new_status=investigation.status,
            comment="Investigation created.",
        )

        create_audit_log(
            request=self.request,
            action="INVESTIGATION_CREATE",
            case=investigation.case,
            description="Investigation created.",
            metadata={
                "investigation_id": investigation.id,
                "investigation_number": investigation.investigation_number,
                "title": investigation.title,
                "status": investigation.status,
                "priority": investigation.priority,
            },
        )

    def perform_update(self, serializer):

        investigation = self.get_object()

        old_status = investigation.status
        old_priority = investigation.priority
        old_lead_id = investigation.lead_investigator_id

        old_officer_ids = list(
            investigation.assigned_officers.values_list(
                "id",
                flat=True,
            )
        )

        investigation = serializer.save()

        new_officer_ids = list(
            investigation.assigned_officers.values_list(
                "id",
                flat=True,
            )
        )

        if old_status != investigation.status:

            InvestigationHistory.objects.create(
                investigation=investigation,
                changed_by=self.request.user,
                old_status=old_status,
                new_status=investigation.status,
                comment="Investigation status updated.",
            )

        create_audit_log(
            request=self.request,
            action="INVESTIGATION_UPDATE",
            case=investigation.case,
            description="Investigation updated.",
            metadata={
                "investigation_id": investigation.id,
                "investigation_number": investigation.investigation_number,
                "old_status": old_status,
                "new_status": investigation.status,
                "old_priority": old_priority,
                "new_priority": investigation.priority,
                "old_lead_investigator_id": old_lead_id,
                "new_lead_investigator_id": investigation.lead_investigator_id,
                "old_assigned_officers": old_officer_ids,
                "new_assigned_officers": new_officer_ids,
            },
        )

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):

        investigation = self.get_object()

        investigation_id = investigation.id
        investigation_number = investigation.investigation_number

        create_audit_log(
            request=request,
            action="INVESTIGATION_DELETE",
            case=investigation.case,
            description="Investigation deleted.",
            metadata={
                "investigation_id": investigation_id,
                "investigation_number": investigation_number,
            },
        )

        investigation.delete()

        return Response(
            {
                "success": True,
                "message": "Investigation deleted successfully.",
                "investigation_id": investigation_id,
                "investigation_number": investigation_number,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="assign",
    )
    @transaction.atomic
    def assign(
        self,
        request,
        pk=None,
    ):

        investigation = self.get_object()

        serializer = InvestigationAssignmentSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        old_lead_id = investigation.lead_investigator_id

        old_officer_ids = list(
            investigation.assigned_officers.values_list(
                "id",
                flat=True,
            )
        )

        update_fields = []

        if "lead_investigator" in serializer.validated_data:

            investigation.lead_investigator = (
                serializer.validated_data["lead_investigator"]
            )

            update_fields.append(
                "lead_investigator"
            )

        if update_fields:

            investigation.save(
                update_fields=update_fields + [
                    "updated_at",
                ]
            )

        if "assigned_officers" in serializer.validated_data:

            investigation.assigned_officers.set(
                serializer.validated_data["assigned_officers"]
            )

        new_officer_ids = list(
            investigation.assigned_officers.values_list(
                "id",
                flat=True,
            )
        )

        create_audit_log(
            request=request,
            action="INVESTIGATION_ASSIGN",
            case=investigation.case,
            description="Investigation investigators and officers assigned.",
            metadata={
                "investigation_id": investigation.id,
                "investigation_number": investigation.investigation_number,
                "old_lead_investigator_id": old_lead_id,
                "new_lead_investigator_id": investigation.lead_investigator_id,
                "old_assigned_officers": old_officer_ids,
                "new_assigned_officers": new_officer_ids,
            },
        )

        investigation.refresh_from_db()

        return Response(
            InvestigationSerializer(
                investigation,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="status",
    )
    @transaction.atomic
    def update_status(
        self,
        request,
        pk=None,
    ):

        investigation = self.get_object()

        serializer = InvestigationStatusSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        new_status = serializer.validated_data["status"]

        comment = serializer.validated_data.get(
            "comment",
            "",
        )

        old_status = investigation.status

        if old_status == new_status:

            return Response(
                {
                    "success": True,
                    "message": "Investigation status is already set to this value.",
                    "status": investigation.status,
                },
                status=status.HTTP_200_OK,
            )

        now = timezone.now()

        investigation.status = new_status

        update_fields = [
            "status",
            "updated_at",
        ]

        if (
            new_status == Investigation.Status.ACTIVE
            and investigation.started_at is None
        ):

            investigation.started_at = now
            update_fields.append("started_at")

        if new_status in [
            Investigation.Status.COMPLETED,
            Investigation.Status.CLOSED,
        ]:

            if investigation.completed_at is None:

                investigation.completed_at = now
                update_fields.append("completed_at")

        investigation.save(
            update_fields=update_fields
        )

        history = InvestigationHistory.objects.create(
            investigation=investigation,
            changed_by=request.user,
            old_status=old_status,
            new_status=new_status,
            comment=comment,
        )

        create_audit_log(
            request=request,
            action="INVESTIGATION_STATUS_CHANGE",
            case=investigation.case,
            description="Investigation status changed.",
            metadata={
                "investigation_id": investigation.id,
                "investigation_number": investigation.investigation_number,
                "old_status": old_status,
                "new_status": new_status,
                "comment": comment,
                "history_id": history.id,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Investigation status updated.",
                "investigation": InvestigationSerializer(
                    investigation,
                    context={"request": request},
                ).data,
                "history": InvestigationTimelineSerializer(
                    history
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="timeline",
    )
    def timeline(
        self,
        request,
        pk=None,
    ):

        investigation = self.get_object()

        history = (
            InvestigationHistory.objects
            .filter(
                investigation=investigation
            )
            .select_related(
                "changed_by"
            )
            .order_by(
                "-created_at"
            )
        )

        serializer = InvestigationTimelineSerializer(
            history,
            many=True,
        )

        return Response(
            {
                "success": True,
                "investigation_id": investigation.id,
                "investigation_number": investigation.investigation_number,
                "case_id": investigation.case_id,
                "count": history.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class WitnessStatementViewSet(viewsets.ModelViewSet):

    serializer_class = WitnessStatementSerializer

    permission_classes = [
        IsAuthenticated,
        WitnessStatementPermission,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    def get_queryset(self):

        user = self.request.user

        if not user.is_authenticated:
            return WitnessStatement.objects.none()

        queryset = (
            WitnessStatement.objects
            .filter(
                is_archived=False
            )
            .select_related(
                "case",
                "recorded_by",
            )
            .prefetch_related(
                "media",
            )
        )

        if user.role == "ADMIN":
            return queryset

        if user.role == "POLICE_OFFICER":
            return queryset.filter(
                Q(case__assigned_officer=user)
                | Q(recorded_by=user)
            ).distinct()

        if user.role == "LEGAL_OFFICER":
            return queryset.filter(
                recorded_by=user
            ).distinct()

        return WitnessStatement.objects.none()

    def _get_uploaded_media(self):

        photos = self.request.FILES.getlist(
            "photo"
        )

        videos = self.request.FILES.getlist(
            "video"
        )

        if not photos:

            photo = self.request.FILES.get(
                "photo"
            )

            if photo:
                photos = [photo]

        if not videos:

            video = self.request.FILES.get(
                "video"
            )

            if video:
                videos = [video]

        return photos, videos

    @transaction.atomic
    def create(
        self,
        request,
        *args,
        **kwargs,
    ):

        photos, videos = self._get_uploaded_media()

        if not photos:

            return Response(
                {
                    "success": False,
                    "message": "Photo is required.",
                    "errors": {
                        "photo": [
                            "At least one photo is required."
                        ]
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not videos:

            return Response(
                {
                    "success": False,
                    "message": "Video is required.",
                    "errors": {
                        "video": [
                            "At least one video is required."
                        ]
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        statement_serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        statement_serializer.is_valid(
            raise_exception=True
        )

        statement = statement_serializer.save(
            recorded_by=request.user
        )

        created_photos = []
        created_videos = []

        for photo in photos:

            media_serializer = WitnessStatementMediaSerializer(
                data={
                    "media_type": WitnessStatementMedia.MediaType.PHOTO,
                    "file": photo,
                },
                context={
                    "request": request,
                },
            )

            media_serializer.is_valid(
                raise_exception=True
            )

            media = media_serializer.save(
                statement=statement,
                uploaded_by=request.user,
            )

            created_photos.append(
                media
            )

        for video in videos:

            media_serializer = WitnessStatementMediaSerializer(
                data={
                    "media_type": WitnessStatementMedia.MediaType.VIDEO,
                    "file": video,
                },
                context={
                    "request": request,
                },
            )

            media_serializer.is_valid(
                raise_exception=True
            )

            media = media_serializer.save(
                statement=statement,
                uploaded_by=request.user,
            )

            created_videos.append(
                media
            )

        photo_exists = statement.media.filter(
            media_type=WitnessStatementMedia.MediaType.PHOTO
        ).exists()

        video_exists = statement.media.filter(
            media_type=WitnessStatementMedia.MediaType.VIDEO
        ).exists()

        if not photo_exists:

            raise serializers.ValidationError(
                {
                    "photo": [
                        "At least one photo is required."
                    ]
                }
            )

        if not video_exists:

            raise serializers.ValidationError(
                {
                    "video": [
                        "At least one video is required."
                    ]
                }
            )

        create_audit_log(
            request=request,
            action="WITNESS_STATEMENT_CREATE",
            case=statement.case,
            description="Witness statement created.",
            metadata={
                "statement_id": statement.id,
                "statement_number": statement.statement_number,
                "witness_reference": statement.witness_reference,
                "classification": statement.classification,
                "status": statement.status,
                "photo_count": len(created_photos),
                "video_count": len(created_videos),
            },
        )

        output_serializer = self.get_serializer(
            statement,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Witness statement created successfully.",
                "data": output_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_update(
        self,
        serializer,
    ):

        statement = serializer.save()

        create_audit_log(
            request=self.request,
            action="WITNESS_STATEMENT_UPDATE",
            case=statement.case,
            description="Witness statement updated.",
            metadata={
                "statement_id": statement.id,
                "statement_number": statement.statement_number,
                "classification": statement.classification,
                "status": statement.status,
            },
        )

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):

        statement = self.get_object()

        statement.is_archived = True

        statement.status = (
            WitnessStatement.StatementStatus.ARCHIVED
        )

        statement.save(
            update_fields=[
                "is_archived",
                "status",
                "updated_at",
            ]
        )

        create_audit_log(
            request=request,
            action="WITNESS_STATEMENT_ARCHIVE",
            case=statement.case,
            description="Witness statement archived.",
            metadata={
                "statement_id": statement.id,
                "statement_number": statement.statement_number,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Witness statement archived successfully.",
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="verify-access",
    )
    def verify_access(
        self,
        request,
        pk=None,
    ):

        statement = self.get_object()

        create_audit_log(
            request=request,
            action="WITNESS_STATEMENT_VERIFY",
            case=statement.case,
            description="Witness statement access verified.",
            metadata={
                "statement_id": statement.id,
                "statement_number": statement.statement_number,
                "classification": statement.classification,
                "status": statement.status,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Authorized access confirmed.",
                "statement_id": statement.id,
                "statement_number": statement.statement_number,
                "case_id": statement.case_id,
                "classification": statement.classification,
                "status": statement.status,
                "is_archived": statement.is_archived,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="media",
        parser_classes=[
            MultiPartParser,
            FormParser,
        ],
    )
    def upload_media(
        self,
        request,
        pk=None,
    ):

        statement = self.get_object()

        serializer = WitnessStatementMediaSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        media = serializer.save(
            statement=statement,
            uploaded_by=request.user,
        )

        create_audit_log(
            request=request,
            action="WITNESS_STATEMENT_MEDIA_UPLOAD",
            case=statement.case,
            description="Witness statement media uploaded.",
            metadata={
                "statement_id": statement.id,
                "statement_number": statement.statement_number,
                "media_id": media.id,
                "media_type": media.media_type,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Witness statement media uploaded successfully.",
                "data": WitnessStatementMediaSerializer(
                    media,
                    context={
                        "request": request,
                    },
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )