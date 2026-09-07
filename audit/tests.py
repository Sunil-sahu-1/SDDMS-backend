from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from .models import AuditLog
from .utils import create_audit_log, verify_audit_chain


User = get_user_model()


class AuditChainTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username="audit_test",
            password="TestPassword123!",
        )

    def make_request(self):
        request = self.factory.get("/test/")
        request.user = self.user
        return request

    def test_audit_chain_is_valid(self):
        request = self.make_request()

        create_audit_log(
            request=request,
            action="CREATE",
            description="First audit record.",
            metadata={
                "test": True,
            },
        )

        create_audit_log(
            request=request,
            action="UPDATE",
            description="Second audit record.",
            metadata={
                "version": 2,
            },
        )

        result = verify_audit_chain()

        self.assertTrue(result["valid"])
        self.assertEqual(result["total_records"], 2)
        self.assertEqual(result["invalid_records"], [])

    def test_audit_chain_detects_tampering(self):
        request = self.make_request()

        create_audit_log(
            request=request,
            action="CREATE",
            description="Original record.",
        )

        log = AuditLog.objects.first()

        # Direct DB update to simulate malicious tampering.
        AuditLog.objects.filter(pk=log.pk).update(
            description="Tampered record."
        )

        result = verify_audit_chain()

        self.assertFalse(result["valid"])
        self.assertEqual(result["total_records"], 1)
        self.assertTrue(
            any(
                error in result["invalid_records"][0]["errors"]
                for error in [
                    "record_hash_mismatch",
                ]
            )
        )

    def test_audit_log_cannot_be_updated(self):
        request = self.make_request()

        log = create_audit_log(
            request=request,
            action="CREATE",
            description="Immutable record.",
        )

        log.description = "Trying to modify"

        with self.assertRaises(ValueError):
            log.save()

    def test_audit_log_cannot_be_deleted(self):
        request = self.make_request()

        log = create_audit_log(
            request=request,
            action="CREATE",
            description="Immutable record.",
        )

        with self.assertRaises(ValueError):
            log.delete()
