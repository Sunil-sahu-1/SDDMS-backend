from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone

from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework_simplejwt.views import TokenObtainPairView

from audit.utils import create_audit_log

from .models import User, UserVerification

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UserVerificationSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    AdminVerificationSerializer,
)

from .permissions import HasRole


class AuditAction:
    LOGIN = "LOGIN"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Registration submitted successfully. Your application is pending administrator verification.",
                "data": {
                    "username": user.username,
                    "role": user.role,
                    "verification_status": user.verification.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class VerificationSubmitView(generics.CreateAPIView):
    serializer_class = UserVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if hasattr(self.request.user, "verification"):
            raise serializers.ValidationError(
                {"detail": "Verification record already exists for this account."}
            )
        serializer.save()


class LoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"success": False, "message": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request=request, username=username, password=password)

        if not user:
            return Response(
                {"success": False, "message": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"success": False, "message": "Your account has been deactivated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.role != User.Role.ADMIN:
            if not hasattr(user, "verification"):
                return Response(
                    {
                        "success": False,
                        "message": "Verification is required before login.",
                        "verification_status": "NOT_SUBMITTED",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if user.verification.status != UserVerification.Status.VERIFIED:
                return Response(
                    {
                        "success": False,
                        "message": "Your account is not verified yet.",
                        "verification_status": user.verification.status,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            create_audit_log(
                request=request,
                action=AuditAction.LOGIN,
                description="User logged in successfully.",
                metadata={"username": user.username, "role": user.role},
            )

        return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(
            {
                "success": True,
                "message": "User profile retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def get(self, request):
        queryset = User.objects.all().order_by("-created_at")
        serializer = AdminUserSerializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "message": "Users retrieved successfully.",
                "count": queryset.count(),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserDetailView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk)
        if user is None:
            return Response({"success": False, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {"success": True, "message": "User retrieved successfully.", "data": AdminUserSerializer(user).data},
            status=status.HTTP_200_OK,
        )

    def patch(self, request, pk):
        user = self.get_object(pk)
        if user is None:
            return Response({"success": False, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            updated_user = serializer.save()
            create_audit_log(
                request=request,
                action=AuditAction.UPDATE,
                description="Administrator updated a user account.",
                metadata={"target_user_id": updated_user.id, "target_username": updated_user.username, "changes": serializer.validated_data},
            )
        return Response(
            {"success": True, "message": "User updated successfully.", "data": AdminUserSerializer(updated_user).data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        user = self.get_object(pk)
        if user is None:
            return Response({"success": False, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.pk == request.user.pk:
            return Response({"success": False, "message": "You cannot delete your own admin account."}, status=status.HTTP_400_BAD_REQUEST)
        target_user_id = user.id
        target_username = user.username
        with transaction.atomic():
            user.delete()
            create_audit_log(
                request=request,
                action=AuditAction.DELETE,
                description="Administrator deleted a user account.",
                metadata={"target_user_id": target_user_id, "target_username": target_username},
            )
        return Response({"success": True, "message": "User deleted successfully."}, status=status.HTTP_200_OK)


class AdminUserRoleView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        new_role = request.data.get("role")
        valid_roles = {choice[0] for choice in User.Role.choices}
        if new_role not in valid_roles:
            return Response({"success": False, "message": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
        if new_role == User.Role.ADMIN and user.pk != request.user.pk:
            return Response({"success": False, "message": "Administrator role cannot be assigned through this endpoint."}, status=status.HTTP_400_BAD_REQUEST)

        old_role = user.role
        with transaction.atomic():
            user.role = new_role
            user.save(update_fields=["role", "updated_at"])
            verification = getattr(user, "verification", None)
            if verification is not None:
                if new_role == User.Role.ADMIN:
                    verification.delete()
                else:
                    verification.verification_type = new_role
                    verification.status = UserVerification.Status.PENDING
                    verification.verified_by = None
                    verification.verified_at = None
                    verification.rejection_reason = None
                    verification.save(update_fields=["verification_type", "status", "verified_by", "verified_at", "rejection_reason", "updated_at"])
            create_audit_log(
                request=request,
                action=AuditAction.UPDATE,
                description="Administrator changed a user's role.",
                metadata={"target_user_id": user.id, "target_username": user.username, "old_role": old_role, "new_role": new_role},
            )
        return Response(
            {"success": True, "message": "User role updated successfully.", "data": {"id": user.id, "username": user.username, "role": user.role}},
            status=status.HTTP_200_OK,
        )


class AdminUserStatusView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"success": False, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if "is_active" not in request.data:
            return Response({"success": False, "message": "is_active is required."}, status=status.HTTP_400_BAD_REQUEST)
        is_active = request.data.get("is_active")
        if not isinstance(is_active, bool):
            return Response({"success": False, "message": "is_active must be a boolean."}, status=status.HTTP_400_BAD_REQUEST)
        if user.pk == request.user.pk and is_active is False:
            return Response({"success": False, "message": "You cannot deactivate your own admin account."}, status=status.HTTP_400_BAD_REQUEST)
        old_status = user.is_active
        if old_status == is_active:
            return Response({"success": True, "message": "User status is already set.", "data": {"id": user.id, "username": user.username, "is_active": user.is_active}}, status=status.HTTP_200_OK)
        with transaction.atomic():
            user.is_active = is_active
            user.save(update_fields=["is_active", "updated_at"])
            create_audit_log(
                request=request,
                action=AuditAction.UPDATE,
                description="Administrator changed user account status.",
                metadata={"target_user_id": user.id, "target_username": user.username, "old_status": old_status, "new_status": is_active},
            )
        return Response(
            {"success": True, "message": "User status updated successfully.", "data": {"id": user.id, "username": user.username, "is_active": user.is_active}},
            status=status.HTTP_200_OK,
        )


class AdminVerificationListView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def get(self, request):
        queryset = UserVerification.objects.select_related("user", "verified_by").order_by("-created_at")
        serializer = AdminVerificationSerializer(queryset, many=True)
        return Response({"success": True, "message": "Verification requests retrieved successfully.", "count": queryset.count(), "data": serializer.data}, status=status.HTTP_200_OK)


class AdminVerificationApproveView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk):
        try:
            verification = UserVerification.objects.select_related("user").get(pk=pk)
        except UserVerification.DoesNotExist:
            return Response({"success": False, "message": "Verification request not found."}, status=status.HTTP_404_NOT_FOUND)
        if verification.status != UserVerification.Status.PENDING:
            return Response({"success": False, "message": "Only pending verification requests can be approved.", "current_status": verification.status}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            verification.status = UserVerification.Status.VERIFIED
            verification.verified_by = request.user
            verification.verified_at = timezone.now()
            verification.rejection_reason = None
            verification.save(update_fields=["status", "verified_by", "verified_at", "rejection_reason", "updated_at"])
            create_audit_log(request=request, action=AuditAction.UPDATE, description="Administrator approved a user verification request.", metadata={"verification_id": verification.id, "target_user_id": verification.user.id, "target_username": verification.user.username, "verification_status": UserVerification.Status.VERIFIED})
        return Response({"success": True, "message": "Verification approved successfully.", "data": AdminVerificationSerializer(verification).data}, status=status.HTTP_200_OK)


class AdminVerificationRejectView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk):
        try:
            verification = UserVerification.objects.select_related("user").get(pk=pk)
        except UserVerification.DoesNotExist:
            return Response({"success": False, "message": "Verification request not found."}, status=status.HTTP_404_NOT_FOUND)
        if verification.status != UserVerification.Status.PENDING:
            return Response({"success": False, "message": "Only pending verification requests can be rejected.", "current_status": verification.status}, status=status.HTTP_400_BAD_REQUEST)
        rejection_reason = str(request.data.get("rejection_reason", "")).strip()
        if not rejection_reason:
            return Response({"success": False, "message": "Rejection reason is required."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            verification.status = UserVerification.Status.REJECTED
            verification.verified_by = request.user
            verification.verified_at = timezone.now()
            verification.rejection_reason = rejection_reason
            verification.save(update_fields=["status", "verified_by", "verified_at", "rejection_reason", "updated_at"])
            create_audit_log(request=request, action=AuditAction.UPDATE, description="Administrator rejected a user verification request.", metadata={"verification_id": verification.id, "target_user_id": verification.user.id, "target_username": verification.user.username, "verification_status": UserVerification.Status.REJECTED, "rejection_reason": rejection_reason})
        return Response({"success": True, "message": "Verification rejected successfully.", "data": AdminVerificationSerializer(verification).data}, status=status.HTTP_200_OK)


class StaffListView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [
        User.Role.ADMIN,
        User.Role.POLICE_OFFICER,
        User.Role.INVESTIGATOR,
        User.Role.LEGAL_OFFICER,
    ]

    def get(self, request):
        queryset = (
            User.objects
            .filter(
                is_active=True,
                verification__status=UserVerification.Status.VERIFIED,
                role__in=[User.Role.POLICE_OFFICER, User.Role.INVESTIGATOR],
            )
            .select_related("verification")
            .order_by("first_name", "last_name", "username")
        )
        data = []
        for user in queryset:
            full_name = f"{user.first_name} {user.last_name}".strip() or user.username
            data.append({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": full_name,
                "role": user.role,
                "is_active": user.is_active,
                "verification_status": user.verification.status,
            })
        return Response({"success": True, "message": "Verified active police officers and investigators retrieved successfully.", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class PoliceOfficerListView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.POLICE_OFFICER, User.Role.INVESTIGATOR, User.Role.LEGAL_OFFICER]

    def get(self, request):
        queryset = User.objects.filter(role=User.Role.POLICE_OFFICER, is_active=True, verification__status=UserVerification.Status.VERIFIED).select_related("verification").order_by("first_name", "last_name", "username")
        data = []
        for user in queryset:
            full_name = f"{user.first_name} {user.last_name}".strip() or user.username
            data.append({"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "full_name": full_name, "role": user.role, "is_active": user.is_active})
        return Response({"success": True, "message": "Verified police officers retrieved successfully.", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class InvestigatorListView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.POLICE_OFFICER, User.Role.INVESTIGATOR, User.Role.LEGAL_OFFICER]

    def get(self, request):
        queryset = User.objects.filter(role=User.Role.INVESTIGATOR, is_active=True, verification__status=UserVerification.Status.VERIFIED).select_related("verification").order_by("first_name", "last_name", "username")
        data = []
        for user in queryset:
            full_name = f"{user.first_name} {user.last_name}".strip() or user.username
            data.append({"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "full_name": full_name, "role": user.role, "is_active": user.is_active})
        return Response({"success": True, "message": "Verified investigators retrieved successfully.", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class ComplainantListView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.POLICE_OFFICER, User.Role.INVESTIGATOR, User.Role.LEGAL_OFFICER]

    def get(self, request):
        queryset = User.objects.filter(role=User.Role.NORMAL_USER, is_active=True).order_by("first_name", "last_name", "username")
        data = []
        for user in queryset:
            full_name = f"{user.first_name} {user.last_name}".strip() or user.username
            data.append({"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "full_name": full_name, "role": user.role, "is_active": user.is_active})
        return Response({"success": True, "message": "Complainants retrieved successfully.", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class StaffTestView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.POLICE_OFFICER, User.Role.INVESTIGATOR, User.Role.LEGAL_OFFICER]

    def get(self, request):
        return Response({"success": True, "role": request.user.role, "message": "Staff access granted."})


class PoliceTestView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.POLICE_OFFICER]

    def get(self, request):
        return Response({"success": True, "role": request.user.role, "message": "Police access granted."})


class InvestigatorTestView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.INVESTIGATOR]

    def get(self, request):
        return Response({"success": True, "role": request.user.role, "message": "Investigator access granted."})


class LegalTestView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.LEGAL_OFFICER]

    def get(self, request):
        return Response({"success": True, "role": request.user.role, "message": "Legal access granted."})


class AdminTestView(APIView):
    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN]

    def get(self, request):
        return Response({"success": True, "role": request.user.role, "message": "Admin access granted."})
