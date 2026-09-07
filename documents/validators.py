from pathlib import Path

from django.core.exceptions import ValidationError


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".jpg",
    ".jpeg",
    ".png",
    ".txt",
}


def validate_document_file(file):

    if file.size > MAX_FILE_SIZE:
        raise ValidationError(
            "File size must not exceed 10 MB."
        )

    extension = Path(file.name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "Unsupported file type."
        )
