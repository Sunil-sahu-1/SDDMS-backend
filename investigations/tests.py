from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from cases.models import Case

from .models import (
    Investigation,
    InvestigationHistory,
    WitnessStatement,
)


User = get_user_model()


class InvestigationAPITestCase(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_test",
            password="TestPass123!",
            role="ADMIN",
        )

        self.investigator = User.objects.create_user(
            username="investigator_test",
            password="TestPass123!",
            role="INVESTIGATOR",
        )

        self.officer = User.objects.create_user(
            username="officer_test",
            password="TestPass123!",
            role="POLICE_OFFICER",
        )

        self.other_investigator = User.objects.create_user(
            username="other_investigator_test",
            password="TestPass123!",
            role="INVESTIGATOR",
        )

        self.case = Case.objects.create(
            case_number="CASE-TEST-001",
            title="Test Criminal Case",
            description="Test case for investigation API.",
            assigned_investigator=self.investigator,
            assigned_officer=self.officer,
            created_by=self.admin,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def list_url(self):
        return reverse("investigation-list")

    def detail_url(self, investigation):
        return reverse(
            "investigation-detail",
            kwargs={"pk": investigation.pk},
        )

    def assign_url(self, investigation):
        return reverse(
            "investigation-assign",
            kwargs={"pk": investigation.pk},
        )

    def status_url(self, investigation):
        return reverse(
            "investigation-update-status",
            kwargs={"pk": investigation.pk},
        )

    def timeline_url(self, investigation):
        return reverse(
            "investigation-timeline",
            kwargs={"pk": investigation.pk},
        )

    def create_investigation(
        self,
        number="INV-TEST-001",
        lead=None,
    ):
        return Investigation.objects.create(
            case=self.case,
            investigation_number=number,
            title="Test Investigation",
            description="Investigation test.",
            lead_investigator=lead,
            created_by=self.admin,
        )

    def test_unauthenticated_user_cannot_list(self):
        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_admin_can_list(self):
        self.create_investigation()

        self.authenticate(self.admin)

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_investigator_can_list_assigned_investigation(self):
        self.create_investigation(
            lead=self.investigator
        )

        self.authenticate(self.investigator)

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_officer_can_list_assigned_investigation(self):
        investigation = self.create_investigation()

        investigation.assigned_officers.add(
            self.officer
        )

        self.authenticate(self.officer)

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_admin_can_create_investigation(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.list_url(),
            {
                "investigation_number": "INV-CREATE-001",
                "case": self.case.id,
                "title": "New Investigation",
                "description": "New investigation.",
                "status": "PENDING",
                "priority": "HIGH",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        investigation = Investigation.objects.get(
            investigation_number="INV-CREATE-001"
        )

        self.assertEqual(
            investigation.created_by_id,
            self.admin.id,
        )

        self.assertTrue(
            InvestigationHistory.objects.filter(
                investigation=investigation
            ).exists()
        )

    def test_investigator_cannot_create_investigation(self):
        self.authenticate(self.investigator)

        response = self.client.post(
            self.list_url(),
            {
                "investigation_number": "INV-INVESTIGATOR-001",
                "case": self.case.id,
                "title": "Unauthorized Investigation",
                "description": "Should not be created.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_officer_cannot_create_investigation(self):
        self.authenticate(self.officer)

        response = self.client.post(
            self.list_url(),
            {
                "investigation_number": "INV-OFFICER-001",
                "case": self.case.id,
                "title": "Officer Investigation",
                "description": "Should not be created.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_lead_investigator_can_access_detail(self):
        investigation = self.create_investigation(
            number="INV-ACCESS-001",
            lead=self.investigator,
        )

        self.authenticate(self.investigator)

        response = self.client.get(
            self.detail_url(investigation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_unrelated_investigator_cannot_access_detail(self):
        other_case = Case.objects.create(
            case_number="CASE-TEST-002",
            title="Other Case",
            description="Other case.",
            assigned_investigator=self.other_investigator,
            created_by=self.admin,
        )

        investigation = Investigation.objects.create(
            case=other_case,
            investigation_number="INV-PRIVATE-001",
            title="Private Investigation",
            description="Private investigation.",
            lead_investigator=self.other_investigator,
            created_by=self.admin,
        )

        self.authenticate(self.investigator)

        response = self.client.get(
            self.detail_url(investigation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_admin_can_update_investigation(self):
        investigation = self.create_investigation(
            number="INV-UPDATE-001"
        )

        self.authenticate(self.admin)

        response = self.client.patch(
            self.detail_url(investigation),
            {
                "title": "Updated Investigation"
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        investigation.refresh_from_db()

        self.assertEqual(
            investigation.title,
            "Updated Investigation",
        )

    def test_admin_can_delete_investigation(self):
        investigation = self.create_investigation(
            number="INV-DELETE-001"
        )

        self.authenticate(self.admin)

        response = self.client.delete(
            self.detail_url(investigation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            Investigation.objects.filter(
                id=investigation.id
            ).exists()
        )

    def test_non_admin_cannot_delete_investigation(self):
        investigation = self.create_investigation(
            number="INV-DELETE-002",
            lead=self.investigator,
        )

        self.authenticate(self.investigator)

        response = self.client.delete(
            self.detail_url(investigation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Investigation.objects.filter(
                id=investigation.id
            ).exists()
        )

    def test_admin_can_assign_investigator_and_officers(self):
        investigation = self.create_investigation(
            number="INV-ASSIGN-001"
        )

        self.authenticate(self.admin)

        response = self.client.post(
            self.assign_url(investigation),
            {
                "lead_investigator": self.investigator.id,
                "assigned_officers": [
                    self.officer.id
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        investigation.refresh_from_db()

        self.assertEqual(
            investigation.lead_investigator_id,
            self.investigator.id,
        )

        self.assertTrue(
            investigation.assigned_officers.filter(
                id=self.officer.id
            ).exists()
        )

    def test_investigator_can_assign_investigation(self):
        investigation = self.create_investigation(
            number="INV-ASSIGN-002",
            lead=self.investigator,
        )

        self.authenticate(self.investigator)

        response = self.client.post(
            self.assign_url(investigation),
            {
                "lead_investigator": self.investigator.id,
                "assigned_officers": [
                    self.officer.id
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_officer_cannot_assign_investigation(self):
        investigation = self.create_investigation(
            number="INV-ASSIGN-003"
        )

        investigation.assigned_officers.add(
            self.officer
        )

        self.authenticate(self.officer)

        response = self.client.post(
            self.assign_url(investigation),
            {
                "lead_investigator": self.investigator.id,
                "assigned_officers": [
                    self.officer.id
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_invalid_lead_investigator_is_rejected(self):
        investigation = self.create_investigation(
            number="INV-ASSIGN-004"
        )

        self.authenticate(self.admin)

        response = self.client.post(
            self.assign_url(investigation),
            {
                "lead_investigator": self.officer.id,
                "assigned_officers": [],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_assigned_user_is_rejected(self):
        investigation = self.create_investigation(
            number="INV-ASSIGN-005"
        )

        self.authenticate(self.admin)

        response = self.client.post(
            self.assign_url(investigation),
            {
                "lead_investigator": self.investigator.id,
                "assigned_officers": [
                    self.admin.id
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_can_change_status(self):
        investigation = self.create_investigation(
            number="INV-STATUS-001"
        )

        self.authenticate(self.admin)

        response = self.client.post(
            self.status_url(investigation),
            {
                "status": "ACTIVE",
                "comment": "Investigation started.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        investigation.refresh_from_db()

        self.assertEqual(
            investigation.status,
            Investigation.Status.ACTIVE,
        )

        self.assertIsNotNone(
            investigation.started_at
        )

    def test_investigator_can_change_status(self):
        investigation = self.create_investigation(
            number="INV-STATUS-002",
            lead=self.investigator,
        )

        self.authenticate(self.investigator)

        response = self.client.post(
            self.status_url(investigation),
            {
                "status": "ON_HOLD",
                "comment": "Investigation paused.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_officer_cannot_change_status(self):
        investigation = self.create_investigation(
            number="INV-STATUS-003"
        )

        investigation.assigned_officers.add(
            self.officer
        )

        self.authenticate(self.officer)

        response = self.client.post(
            self.status_url(investigation),
            {
                "status": "ACTIVE"
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_completed_status_sets_completed_at(self):
        investigation = self.create_investigation(
            number="INV-STATUS-004"
        )

        self.authenticate(self.admin)

        response = self.client.post(
            self.status_url(investigation),
            {
                "status": "COMPLETED",
                "comment": "Investigation completed.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        investigation.refresh_from_db()

        self.assertEqual(
            investigation.status,
            Investigation.Status.COMPLETED,
        )

        self.assertIsNotNone(
            investigation.completed_at
        )

    def test_status_change_creates_history(self):
        investigation = self.create_investigation(
            number="INV-HISTORY-001"
        )

        self.authenticate(self.admin)

        self.client.post(
            self.status_url(investigation),
            {
                "status": "ACTIVE",
                "comment": "Started.",
            },
            format="json",
        )

        history = InvestigationHistory.objects.filter(
            investigation=investigation,
            new_status="ACTIVE",
        )

        self.assertTrue(
            history.exists()
        )

        self.assertEqual(
            history.first().changed_by_id,
            self.admin.id,
        )

    def test_timeline_endpoint(self):
        investigation = self.create_investigation(
            number="INV-TIMELINE-001"
        )

        self.authenticate(self.admin)

        self.client.post(
            self.status_url(investigation),
            {
                "status": "ACTIVE",
                "comment": "Started.",
            },
            format="json",
        )

        response = self.client.get(
            self.timeline_url(investigation)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["investigation_id"],
            investigation.id,
        )

        self.assertGreaterEqual(
            response.data["count"],
            1,
        )


class WitnessStatementAPITestCase(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="ws_admin",
            password="TestPass123!",
            role="ADMIN",
        )

        self.investigator = User.objects.create_user(
            username="ws_investigator",
            password="TestPass123!",
            role="INVESTIGATOR",
        )

        self.officer = User.objects.create_user(
            username="ws_officer",
            password="TestPass123!",
            role="POLICE_OFFICER",
        )

        self.case = Case.objects.create(
            case_number="CASE-WS-001",
            title="Witness Test Case",
            description="Witness statement test case.",
            assigned_investigator=self.investigator,
            assigned_officer=self.officer,
            created_by=self.admin,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def list_url(self):
        return reverse(
            "witness-statement-list"
        )

    def detail_url(self, statement):
        return reverse(
            "witness-statement-detail",
            kwargs={"pk": statement.pk},
        )

    def create_statement(self):
        return WitnessStatement.objects.create(
            case=self.case,
            witness_name="Test Witness",
            witness_contact="9999999999",
            statement=(
                "This is a valid witness statement "
                "for testing."
            ),
            recorded_by=self.officer,
            statement_date="2026-01-01T10:00:00Z",
        )

    def test_unauthenticated_user_cannot_list(self):
        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_officer_can_list_statements(self):
        self.create_statement()

        self.authenticate(self.officer)

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_investigator_can_list_statements(self):
        self.create_statement()

        self.authenticate(self.investigator)

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            1,
        )

    def test_admin_can_list_statements(self):
        self.create_statement()

        self.authenticate(self.admin)

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_officer_can_create_statement(self):
        self.authenticate(self.officer)

        response = self.client.post(
            self.list_url(),
            {
                "case": self.case.id,
                "witness_name": "New Witness",
                "witness_contact": "8888888888",
                "statement": (
                    "This is a valid witness statement."
                ),
                "statement_date": (
                    "2026-01-01T10:00:00Z"
                ),
                "status": "DRAFT",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        statement = WitnessStatement.objects.get(
            witness_name="New Witness"
        )

        self.assertEqual(
            statement.recorded_by_id,
            self.officer.id,
        )

    def test_short_witness_name_is_rejected(self):
        self.authenticate(self.officer)

        response = self.client.post(
            self.list_url(),
            {
                "case": self.case.id,
                "witness_name": "A",
                "statement": (
                    "This is a sufficiently long statement."
                ),
                "statement_date": (
                    "2026-01-01T10:00:00Z"
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_short_statement_is_rejected(self):
        self.authenticate(self.officer)

        response = self.client.post(
            self.list_url(),
            {
                "case": self.case.id,
                "witness_name": "Valid Witness",
                "statement": "Too short",
                "statement_date": (
                    "2026-01-01T10:00:00Z"
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_can_update_statement(self):
        statement = self.create_statement()

        self.authenticate(self.admin)

        response = self.client.patch(
            self.detail_url(statement),
            {
                "witness_name": "Updated Witness"
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        statement.refresh_from_db()

        self.assertEqual(
            statement.witness_name,
            "Updated Witness",
        )

    def test_admin_can_archive_statement(self):
        statement = self.create_statement()

        self.authenticate(self.admin)

        response = self.client.delete(
            self.detail_url(statement)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        statement.refresh_from_db()

        self.assertTrue(
            statement.is_archived
        )

        self.assertEqual(
            statement.status,
            WitnessStatement.StatementStatus.ARCHIVED,
        )

    def test_archived_statement_not_in_list(self):
        statement = self.create_statement()

        statement.is_archived = True
        statement.status = (
            WitnessStatement.StatementStatus.ARCHIVED
        )
        statement.save()

        self.authenticate(self.admin)

        response = self.client.get(
            self.list_url()
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data),
            0,
        )

    def test_verify_access_endpoint(self):
        statement = self.create_statement()

        self.authenticate(self.officer)

        url = reverse(
            "witness-statement-verify-access",
            kwargs={"pk": statement.pk},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertEqual(
            response.data["statement_id"],
            statement.id,
        )
