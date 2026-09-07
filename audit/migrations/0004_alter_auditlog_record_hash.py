from django.db import migrations, models


def fill_missing_hashes(apps, schema_editor):
    AuditLog = apps.get_model("audit", "AuditLog")

    import hashlib
    import json

    logs = AuditLog.objects.filter(
        record_hash__isnull=True
    ).order_by("id")

    previous_hash = None

    existing_last = (
        AuditLog.objects
        .exclude(record_hash__isnull=True)
        .exclude(record_hash="")
        .order_by("-id")
        .first()
    )

    if existing_last:
        previous_hash = existing_last.record_hash

    for log in logs:
        payload = {
            "user_id": log.user_id,
            "action": log.action,
            "case_id": log.case_id,
            "document_id": log.document_id,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "metadata": log.metadata or {},
            "previous_hash": previous_hash,
            "created_at": log.created_at.isoformat(),
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        record_hash = hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

        log.previous_hash = previous_hash
        log.record_hash = record_hash

        log.save(
            update_fields=[
                "previous_hash",
                "record_hash",
            ]
        )

        previous_hash = record_hash


class Migration(migrations.Migration):

    dependencies = [
        (
            "audit",
            "0003_alter_auditlog_action",
        ),
    ]

    operations = [
        migrations.RunPython(
            fill_missing_hashes,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="record_hash",
            field=models.CharField(
                max_length=64,
                unique=True,
                editable=False,
            ),
        ),
    ]
