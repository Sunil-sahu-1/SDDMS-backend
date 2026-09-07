from pathlib import Path

from django.core.exceptions import ValidationError


MAX_EVIDENCE_SIZE = 50 * 1024 * 1024  # 50 MB

ALLOWED_EVIDENCE_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".txt",
    ".doc",
    ".docx",
    ".mp3",
    ".wav",
    ".mp4",
    ".mov",
}


def validate_evidence_file(file):

    if file.size > MAX_EVIDENCE_SIZE:
        raise ValidationError(
            "Evidence file cannot exceed 50 MB."
        )

    extension = Path(
        file.name
    ).suffix.lower()

    if extension not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise ValidationError(
            "Unsupported evidence file type."
        )
