import hashlib
import json

from django.utils import timezone

from .models import AuditLog


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def get_previous_hash():
    last_log = (
        AuditLog.objects
        .filter(record_hash__isnull=False)
        .exclude(record_hash="")
        .order_by("-id")
        .values("record_hash")
        .first()
    )

    if not last_log:
        return None

    return last_log["record_hash"]


def calculate_record_hash(
    user_id,
    action,
    case_id,
    document_id,
    description,
    ip_address,
    user_agent,
    metadata,
    previous_hash,
    created_at,
):
    payload = {
        "user_id": user_id,
        "action": action,
        "case_id": case_id,
        "document_id": document_id,
        "description": description,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "metadata": metadata or {},
        "previous_hash": previous_hash,
        "created_at": created_at.isoformat(),
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def create_audit_log(
    request,
    action,
    case=None,
    document=None,
    description="",
    metadata=None,
):
    if not request.user.is_authenticated:
        return None

    metadata = metadata or {}

    ip_address = get_client_ip(request)

    user_agent = request.META.get(
        "HTTP_USER_AGENT",
        "",
    )

    previous_hash = get_previous_hash()

    created_at = timezone.now()

    audit_log = AuditLog(
        user=request.user,
        action=action,
        case=case,
        document=document,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata,
        previous_hash=previous_hash,
        created_at=created_at,
    )

    audit_log.record_hash = calculate_record_hash(
        user_id=audit_log.user_id,
        action=audit_log.action,
        case_id=audit_log.case_id,
        document_id=audit_log.document_id,
        description=audit_log.description,
        ip_address=audit_log.ip_address,
        user_agent=audit_log.user_agent,
        metadata=audit_log.metadata,
        previous_hash=audit_log.previous_hash,
        created_at=audit_log.created_at,
    )

    audit_log.save()

    return audit_log


def verify_audit_chain():
    logs = list(
        AuditLog.objects
        .select_related(
            "user",
            "case",
            "document",
        )
        .order_by("id")
    )

    if not logs:
        return {
            "valid": True,
            "total_records": 0,
            "invalid_records": [],
            "message": "Audit chain is valid.",
        }

    invalid_records = []

    expected_previous_hash = None

    for log in logs:
        calculated_hash = calculate_record_hash(
            user_id=log.user_id,
            action=log.action,
            case_id=log.case_id,
            document_id=log.document_id,
            description=log.description,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            metadata=log.metadata,
            previous_hash=log.previous_hash,
            created_at=log.created_at,
        )

        errors = []

        if log.previous_hash != expected_previous_hash:
            errors.append(
                "previous_hash_mismatch"
            )

        if log.record_hash != calculated_hash:
            errors.append(
                "record_hash_mismatch"
            )

        if errors:
            invalid_records.append(
                {
                    "id": log.id,
                    "errors": errors,
                    "stored_previous_hash": log.previous_hash,
                    "expected_previous_hash": expected_previous_hash,
                    "stored_record_hash": log.record_hash,
                    "calculated_record_hash": calculated_hash,
                }
            )

        expected_previous_hash = log.record_hash

    return {
        "valid": len(invalid_records) == 0,
        "total_records": len(logs),
        "invalid_records": invalid_records,
        "message": (
            "Audit chain is valid."
            if not invalid_records
            else "Audit chain integrity violation detected."
        ),
    }
