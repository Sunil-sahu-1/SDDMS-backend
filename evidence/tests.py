import hashlib
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from cases.models import Case
from .models import Evidence


class EvidenceAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(
            username="evidence_admin",
            password="TestPassword123!",
            role="ADMIN",
        )

        self.officer = User.objects.create_user(
            username="evidence_officer",
            password="TestPassword123!",
            role="POLICE_OFFICER",
        )

        self.other_officer = User.objects.create_user(
            username="other_officer",
            password="TestPassword123!",
            role="POLICE_OFFICER",
        )

        # Generate unique case numbers for every test run
        self.case = Case.objects.create(
            case_number=f"TEST-{uuid.uuid4().hex[:8].upper()}",
            title="Evidence Test Case",
            assigned_officer=self.officer,
        )

        self.other_case = Case.objects.create(
            case_number=f"TEST-{uuid.uuid4().hex[:8].upper()}",
            title="Other Evidence Case",
            assigned_officer=self.other_officer,
        )

        self.file_content = b"Original evidence content."

        self.uploaded_file = SimpleUploadedFile(
            "evidence.txt",
            self.file_content,
            content_type="text/plain",
        )

    def create_evidence(self, user=None, case=None):
        user = user or self.officer
        case = case or self.case

        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/evidence/",
            {
                "case": case.id,
                "title": "Test Evidence",
                "description": "Evidence test record.",
                "evidence_type": "DOCUMENT",
                "file": self.uploaded_file,
            },
            format="multipart",
        )

        return response

    def test_evidence_create(self):
        response = self.create_evidence()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["id"])
        self.assertEqual(
            response.data["title"],
            "Test Evidence",
        )

        evidence = Evidence.objects.get(
            id=response.data["id"]
        )

        expected_hash = hashlib.sha256(
            self.file_content
        ).hexdigest()

        self.assertEqual(
            evidence.sha256_hash,
            expected_hash,
        )

    def test_evidence_list(self):
        self.create_evidence()

        response = self.client.get(
            "/api/evidence/"
        )

        self.assertEqual(response.status_code, 200)

    def test_evidence_detail(self):
        response = self.create_evidence()

        evidence_id = response.data["id"]

        response = self.client.get(
            f"/api/evidence/{evidence_id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["id"],
            evidence_id,
        )

    def test_evidence_download(self):
        response = self.create_evidence()

        evidence_id = response.data["id"]

        response = self.client.get(
            f"/api/evidence/{evidence_id}/download/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="evidence.txt"',
        )

    def test_evidence_integrity_valid(self):
        response = self.create_evidence()

        evidence_id = response.data["id"]

        response = self.client.get(
            f"/api/evidence/{evidence_id}/verify-integrity/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.data["integrity_valid"]
        )

    def test_evidence_integrity_detects_tampering(self):
        response = self.create_evidence()

        evidence_id = response.data["id"]

        evidence = Evidence.objects.get(
            id=evidence_id
        )

        Evidence.objects.filter(
            id=evidence.id
        ).update(
            sha256_hash="0" * 64
        )

        response = self.client.get(
            f"/api/evidence/{evidence_id}/verify-integrity/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            response.data["integrity_valid"]
        )

    def test_unauthenticated_user_cannot_access_evidence(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            "/api/evidence/"
        )

        self.assertEqual(response.status_code, 401)

    def test_other_officer_cannot_access_evidence(self):
        response = self.create_evidence()

        evidence_id = response.data["id"]

        self.client.force_authenticate(
            user=self.other_officer
        )

        response = self.client.get(
            f"/api/evidence/{evidence_id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_can_access_evidence(self):
        response = self.create_evidence()

        evidence_id = response.data["id"]

        self.client.force_authenticate(
            user=self.admin
        )

        response = self.client.get(
            f"/api/evidence/{evidence_id}/"
        )

        self.assertEqual(response.status_code, 200)

    def test_archived_evidence_cannot_be_downloaded(self):
        response = self.create_evidence()

        evidence_id = response.data["id"]

        Evidence.objects.filter(
            id=evidence_id
        ).update(
            is_archived=True
        )

        response = self.client.get(
            f"/api/evidence/{evidence_id}/download/"
        )

        self.assertEqual(response.status_code, 404)

    def test_evidence_hash_is_sha256(self):
        response = self.create_evidence()

        evidence = Evidence.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            len(evidence.sha256_hash),
            64,
        )

        self.assertEqual(
            evidence.sha256_hash,
            hashlib.sha256(
                self.file_content
            ).hexdigest(),
        )
