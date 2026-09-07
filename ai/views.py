import json
import requests

from django.conf import settings
from django.http import Http404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaffOrAdmin

from cases.models import Case
from complaints.models import Complaint
from investigations.models import (
    Investigation,
    InvestigationHistory,
    WitnessStatement,
)
from evidence.models import (
    Evidence,
    EvidenceCustodyTransfer,
    EvidenceActivity,
)
from documents.models import (
    Document,
    DocumentVersion,
    DocumentShare,
    DocumentSignature,
)
from legal.models import (
    LegalReview,
    CourtHearing,
)

from .serializers import (
    AIRequestSerializer,
)


# ============================================================
# SETTINGS
# ============================================================

OLLAMA_URL = getattr(
    settings,
    "OLLAMA_URL",
    "http://127.0.0.1:11434/api/generate",
)

OLLAMA_MODEL = getattr(
    settings,
    "OLLAMA_MODEL",
    "llama3.2",
)


# ============================================================
# OLLAMA
# ============================================================

def ask_ollama(prompt):
    """
    Send prompt to Ollama and return generated text response.
    """

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=180,
        )

        response.raise_for_status()

        data = response.json()

        result = data.get("response", "")

        if not result:
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return result.strip()

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Ollama is not running. "
            "Please start Ollama and try again."
        )

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Ollama request timed out."
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Unable to connect to Ollama: {error}"
        )


# ============================================================
# SAFE VALUE HELPERS
# ============================================================

def safe_value(value):
    """
    Convert Django/model values into safe strings.
    """

    if value is None:
        return ""

    return str(value)


def user_info(user):
    """
    Return non-sensitive basic user information.
    """

    if not user:
        return None

    return {
        "id": user.id,
        "username": getattr(user, "username", ""),
        "name": (
            getattr(user, "get_full_name", lambda: "")()
            or getattr(user, "username", "")
        ),
    }


# ============================================================
# FILE TEXT EXTRACTION
# ============================================================

def extract_pdf_text(file_field):
    """
    Extract text from PDF files.

    Requires:
        pip install pypdf
    """

    if not file_field:
        return ""

    try:
        from pypdf import PdfReader

        file_field.open("rb")

        reader = PdfReader(file_field)

        pages = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

        file_field.close()

        return "\n".join(pages).strip()

    except Exception:
        try:
            file_field.close()
        except Exception:
            pass

        return ""


def extract_docx_text(file_field):
    """
    Extract text from DOCX files.

    Requires:
        pip install python-docx
    """

    if not file_field:
        return ""

    try:
        from docx import Document as DocxDocument

        file_field.open("rb")

        document = DocxDocument(file_field)

        paragraphs = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(
                    paragraph.text.strip()
                )

        file_field.close()

        return "\n".join(paragraphs).strip()

    except Exception:
        try:
            file_field.close()
        except Exception:
            pass

        return ""


def extract_file_text(file_field, mime_type=""):
    """
    Extract readable text from supported files.
    """

    if not file_field:
        return ""

    filename = safe_value(
        getattr(file_field, "name", "")
    ).lower()

    mime_type = safe_value(
        mime_type
    ).lower()

    # PDF
    if (
        filename.endswith(".pdf")
        or "application/pdf" in mime_type
    ):
        return extract_pdf_text(file_field)

    # DOCX
    if (
        filename.endswith(".docx")
        or "wordprocessingml" in mime_type
    ):
        return extract_docx_text(file_field)

    # TXT / plain text
    if (
        filename.endswith(".txt")
        or mime_type.startswith("text/")
    ):
        try:
            file_field.open("rb")

            content = file_field.read()

            file_field.close()

            return content.decode(
                "utf-8",
                errors="ignore",
            ).strip()

        except Exception:
            try:
                file_field.close()
            except Exception:
                pass

    return ""


# ============================================================
# CASE DATA COLLECTOR
# ============================================================

def collect_case_data(case):
    """
    Collect all data related to one Case.
    """

    data = {
        "case": {},
        "complaint": None,
        "investigations": [],
        "investigation_history": [],
        "witness_statements": [],
        "evidence": [],
        "evidence_custody": [],
        "evidence_activity": [],
        "documents": [],
        "document_versions": [],
        "document_shares": [],
        "document_signatures": [],
        "legal_reviews": [],
        "court_hearings": [],
        "case_history": [],
    }

    # ========================================================
    # CASE
    # ========================================================

    data["case"] = {
        "id": case.id,
        "case_number": case.case_number,
        "fir_number": case.fir_number,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "created_at": safe_value(case.created_at),
        "updated_at": safe_value(case.updated_at),
        "complainant": user_info(
            case.complainant
        ),
        "assigned_officer": user_info(
            case.assigned_officer
        ),
        "assigned_investigator": user_info(
            case.assigned_investigator
        ),
        "assigned_legal_officer": user_info(
            case.assigned_legal_officer
        ),
        "created_by": user_info(
            case.created_by
        ),
    }

    # ========================================================
    # COMPLAINT
    # ========================================================

    complaint = getattr(
        case,
        "complaint",
        None,
    )

    if complaint:
        data["complaint"] = {
            "id": complaint.id,
            "complaint_number": complaint.complaint_number,
            "subject": complaint.subject,
            "description": complaint.description,
            "status": complaint.status,
            "complainant": user_info(
                complaint.complainant
            ),
            "created_at": safe_value(
                complaint.created_at
            ),
            "updated_at": safe_value(
                complaint.updated_at
            ),
        }

    # ========================================================
    # INVESTIGATIONS
    # ========================================================

    investigations = (
        Investigation.objects
        .filter(case=case)
        .select_related(
            "lead_investigator",
            "created_by",
        )
    )

    for investigation in investigations:

        assigned_officers = []

        for officer in (
            investigation.assigned_officers.all()
        ):
            assigned_officers.append(
                user_info(officer)
            )

        data["investigations"].append({
            "id": investigation.id,
            "investigation_number":
                investigation.investigation_number,
            "title":
                investigation.title,
            "description":
                investigation.description,
            "status":
                investigation.status,
            "priority":
                investigation.priority,
            "started_at":
                safe_value(
                    investigation.started_at
                ),
            "completed_at":
                safe_value(
                    investigation.completed_at
                ),
            "lead_investigator":
                user_info(
                    investigation.lead_investigator
                ),
            "assigned_officers":
                assigned_officers,
            "created_by":
                user_info(
                    investigation.created_by
                ),
            "created_at":
                safe_value(
                    investigation.created_at
                ),
            "updated_at":
                safe_value(
                    investigation.updated_at
                ),
        })

        # Investigation history
        histories = (
            InvestigationHistory.objects
            .filter(
                investigation=investigation
            )
            .select_related("changed_by")
        )

        for history in histories:
            data["investigation_history"].append({
                "investigation_number":
                    investigation.investigation_number,
                "old_status":
                    history.old_status,
                "new_status":
                    history.new_status,
                "comment":
                    history.comment,
                "changed_by":
                    user_info(
                        history.changed_by
                    ),
                "created_at":
                    safe_value(
                        history.created_at
                    ),
            })

    # ========================================================
    # WITNESS STATEMENTS
    # ========================================================

    witness_statements = (
        WitnessStatement.objects
        .filter(case=case)
        .select_related("recorded_by")
    )

    for statement in witness_statements:

        data["witness_statements"].append({
            "id": statement.id,
            "statement_number":
                statement.statement_number,
            "witness_reference":
                statement.witness_reference,
            "witness_name":
                statement.witness_name,
            "witness_contact":
                statement.witness_contact,
            "statement":
                statement.statement,
            "recorded_by":
                user_info(
                    statement.recorded_by
                ),
            "statement_date":
                safe_value(
                    statement.statement_date
                ),
            "classification":
                statement.classification,
            "status":
                statement.status,
            "is_archived":
                statement.is_archived,
            "created_at":
                safe_value(
                    statement.created_at
                ),
            "updated_at":
                safe_value(
                    statement.updated_at
                ),
        })

    # ========================================================
    # EVIDENCE
    # ========================================================

    evidence_records = (
        Evidence.objects
        .filter(case=case)
        .select_related(
            "collected_by",
            "current_custodian",
        )
    )

    for evidence in evidence_records:

        evidence_text = extract_file_text(
            evidence.file,
            evidence.mime_type,
        )

        data["evidence"].append({
            "id": evidence.id,
            "evidence_number":
                evidence.evidence_number,
            "title":
                evidence.title,
            "description":
                evidence.description,
            "evidence_type":
                evidence.evidence_type,
            "original_filename":
                evidence.original_filename,
            "file_size":
                evidence.file_size,
            "mime_type":
                evidence.mime_type,
            "sha256_hash":
                evidence.sha256_hash,
            "collected_by":
                user_info(
                    evidence.collected_by
                ),
            "current_custodian":
                user_info(
                    evidence.current_custodian
                ),
            "is_archived":
                evidence.is_archived,
            "created_at":
                safe_value(
                    evidence.created_at
                ),
            "updated_at":
                safe_value(
                    evidence.updated_at
                ),
            "file_text":
                evidence_text,
        })

        # ----------------------------------------------------
        # Evidence custody
        # ----------------------------------------------------

        custody_records = (
            EvidenceCustodyTransfer.objects
            .filter(evidence=evidence)
            .select_related(
                "from_user",
                "to_user",
                "transferred_by",
            )
        )

        for custody in custody_records:

            data["evidence_custody"].append({
                "evidence_number":
                    evidence.evidence_number,
                "from_user":
                    user_info(
                        custody.from_user
                    ),
                "to_user":
                    user_info(
                        custody.to_user
                    ),
                "transferred_by":
                    user_info(
                        custody.transferred_by
                    ),
                "transfer_type":
                    custody.transfer_type,
                "reason":
                    custody.reason,
                "location":
                    custody.location,
                "sha256_hash":
                    custody.sha256_hash,
                "transferred_at":
                    safe_value(
                        custody.transferred_at
                    ),
            })

        # ----------------------------------------------------
        # Evidence activity
        # ----------------------------------------------------

        activities = (
            EvidenceActivity.objects
            .filter(evidence=evidence)
            .select_related("actor")
        )

        for activity in activities:

            data["evidence_activity"].append({
                "evidence_number":
                    evidence.evidence_number,
                "actor":
                    user_info(
                        activity.actor
                    ),
                "action":
                    activity.action,
                "description":
                    activity.description,
                "metadata":
                    activity.metadata,
                "created_at":
                    safe_value(
                        activity.created_at
                    ),
            })

    # ========================================================
    # DOCUMENTS
    # ========================================================

    documents = (
        Document.objects
        .filter(case=case)
        .select_related("uploaded_by")
    )

    for document in documents:

        document_text = extract_file_text(
            document.file,
            document.mime_type,
        )

        data["documents"].append({
            "id": document.id,
            "title":
                document.title,
            "document_type":
                document.document_type,
            "original_filename":
                document.original_filename,
            "file_size":
                document.file_size,
            "mime_type":
                document.mime_type,
            "sha256_hash":
                document.sha256_hash,
            "version":
                document.version,
            "uploaded_by":
                user_info(
                    document.uploaded_by
                ),
            "is_archived":
                document.is_archived,
            "created_at":
                safe_value(
                    document.created_at
                ),
            "updated_at":
                safe_value(
                    document.updated_at
                ),
            "file_text":
                document_text,
        })

        # ----------------------------------------------------
        # Document versions
        # ----------------------------------------------------

        versions = (
            DocumentVersion.objects
            .filter(document=document)
            .select_related("uploaded_by")
        )

        for version in versions:

            version_text = extract_file_text(
                version.file,
                version.mime_type,
            )

            data["document_versions"].append({
                "document_id":
                    document.id,
                "document_title":
                    document.title,
                "version_number":
                    version.version_number,
                "original_filename":
                    version.original_filename,
                "file_size":
                    version.file_size,
                "mime_type":
                    version.mime_type,
                "sha256_hash":
                    version.sha256_hash,
                "uploaded_by":
                    user_info(
                        version.uploaded_by
                    ),
                "change_note":
                    version.change_note,
                "created_at":
                    safe_value(
                        version.created_at
                    ),
                "file_text":
                    version_text,
            })

        # ----------------------------------------------------
        # Document shares
        # ----------------------------------------------------

        shares = (
            DocumentShare.objects
            .filter(document=document)
            .select_related(
                "shared_with",
                "shared_by",
            )
        )

        for share in shares:

            data["document_shares"].append({
                "document_id":
                    document.id,
                "document_title":
                    document.title,
                "shared_with":
                    user_info(
                        share.shared_with
                    ),
                "shared_by":
                    user_info(
                        share.shared_by
                    ),
                "permission":
                    share.permission,
                "expires_at":
                    safe_value(
                        share.expires_at
                    ),
                "is_active":
                    share.is_active,
                "created_at":
                    safe_value(
                        share.created_at
                    ),
            })

        # ----------------------------------------------------
        # Document signatures
        # ----------------------------------------------------

        signatures = (
            DocumentSignature.objects
            .filter(document=document)
            .select_related("signed_by")
        )

        for signature in signatures:

            data["document_signatures"].append({
                "document_id":
                    document.id,
                "document_title":
                    document.title,
                "signed_by":
                    user_info(
                        signature.signed_by
                    ),
                "version":
                    signature.version,
                "document_hash":
                    signature.document_hash,
                "algorithm":
                    signature.algorithm,
                "signed_at":
                    safe_value(
                        signature.signed_at
                    ),
            })

    # ========================================================
    # LEGAL REVIEWS
    # ========================================================

    legal_reviews = (
        LegalReview.objects
        .filter(case=case)
        .select_related("legal_officer")
    )

    for review in legal_reviews:

        data["legal_reviews"].append({
            "id":
                review.id,
            "title":
                review.title,
            "legal_opinion":
                review.legal_opinion,
            "status":
                review.status,
            "remarks":
                review.remarks,
            "legal_officer":
                user_info(
                    review.legal_officer
                ),
            "reviewed_at":
                safe_value(
                    review.reviewed_at
                ),
            "is_archived":
                review.is_archived,
            "created_at":
                safe_value(
                    review.created_at
                ),
            "updated_at":
                safe_value(
                    review.updated_at
                ),
        })

    # ========================================================
    # COURT HEARINGS
    # ========================================================

    hearings = (
        CourtHearing.objects
        .filter(case=case)
        .select_related("legal_officer")
    )

    for hearing in hearings:

        data["court_hearings"].append({
            "id":
                hearing.id,
            "court_name":
                hearing.court_name,
            "hearing_date":
                safe_value(
                    hearing.hearing_date
                ),
            "hearing_purpose":
                hearing.hearing_purpose,
            "status":
                hearing.status,
            "outcome":
                hearing.outcome,
            "legal_officer":
                user_info(
                    hearing.legal_officer
                ),
            "is_archived":
                hearing.is_archived,
            "created_at":
                safe_value(
                    hearing.created_at
                ),
            "updated_at":
                safe_value(
                    hearing.updated_at
                ),
        })

    # ========================================================
    # CASE HISTORY
    # ========================================================

    histories = (
        case.history
        .all()
        .select_related("changed_by")
    )

    for history in histories:

        data["case_history"].append({
            "old_status":
                history.old_status,
            "new_status":
                history.new_status,
            "comment":
                history.comment,
            "changed_by":
                user_info(
                    history.changed_by
                ),
            "created_at":
                safe_value(
                    history.created_at
                ),
        })

    return data


# ============================================================
# AI PROMPTS
# ============================================================

def build_analysis_prompt(case_data):
    """
    Build complete investigation-analysis prompt.

    AI OUTPUT:
        Plain text only.
    """

    json_data = json.dumps(
        case_data,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

    return f"""
You are an AI assistant for a Police and Investigation
Case Management System.

You are reviewing ONE specific case.

IMPORTANT RULES:

1. The case number is only an identifier.
2. Analyze ONLY the data supplied below.
3. Do NOT invent facts.
4. Do NOT assume missing information.
5. Do NOT mix information from another case.
6. Clearly identify missing information.
7. Distinguish allegations from verified facts.
8. Do not declare a person guilty or innocent.
9. Do not fabricate legal conclusions.
10. If evidence is unavailable, say "Not available".
11. If a document file exists but readable text could not be
    extracted, clearly mention that the file exists but readable
    text was not available.
12. Use dates and timeline information when available.
13. Compare complaint, FIR information, police/investigation
    information, witness statements, evidence, legal reviews
    and court hearings.
14. Identify contradictions only when there is an actual
    difference between supplied records.
15. Identify pending actions from statuses, incomplete work,
    missing outcomes, pending reviews, scheduled hearings, etc.
16. Do not create information that is not present in the case data.
17. Keep the response professional and suitable for an official
    case management system.

OUTPUT FORMAT:

Return ONLY plain text.

Do NOT return JSON.
Do NOT use Markdown code fences.
Do NOT return XML.
Do NOT return HTML.
Do NOT return a JSON object.
Do NOT add an introduction before Section 1.
Do NOT add a conclusion after Section 16.

Prepare these EXACT sections:

1. Case Overview
2. Complaint Review
3. FIR Review
4. Police Report Review
5. Investigation Review
6. Evidence Review
7. Documents Review
8. Legal Information
9. Case Timeline
10. Important People
11. Important Dates
12. Contradictions / Inconsistencies
13. Missing Information
14. Pending Actions
15. Important Observations
16. Overall Case Assessment

For every section:

- Use information from the supplied case data.
- Be factual and professional.
- Do not invent anything.
- If there is no relevant information, write:
  "No relevant information available in the case records."

CASE DATA:

{json_data}
"""


def build_summary_prompt(case_data):
    """
    Build complete case summary prompt.

    AI OUTPUT:
        Plain text only.
    """

    json_data = json.dumps(
        case_data,
        indent=2,
        ensure_ascii=False,
        default=str,
    )

    return f"""
You are an AI assistant for a Police and Investigation
Case Management System.

Create a professional summary of the case below.

IMPORTANT RULES:

1. Analyze ONLY the supplied database information.
2. Do not invent facts.
3. Do not mix another case into this case.
4. Keep important names, dates, locations and case numbers.
5. Mention complaint, FIR, investigation, evidence,
   documents, witnesses, legal information and court activity
   where available.
6. Clearly identify missing information.
7. Distinguish allegations from established record information.
8. Do not declare anyone guilty or innocent.
9. Do not fabricate legal conclusions.
10. If information is unavailable, write "Not available".
11. Use only information present in the supplied case data.

OUTPUT FORMAT:

Return ONLY plain text.

Do NOT return JSON.
Do NOT use Markdown code fences.
Do NOT return XML.
Do NOT return HTML.
Do NOT return a JSON object.
Do NOT add an introduction before Section 1.
Do NOT add a conclusion after Section 12.

Return these EXACT sections:

1. Case Summary
2. Complaint
3. FIR / Police Information
4. Investigation
5. Witnesses
6. Evidence
7. Documents
8. Legal / Court Information
9. Timeline
10. Important Observations
11. Missing / Pending Information
12. Overall Summary

For every section:

- Use only supplied case data.
- Keep the information factual.
- Do not invent anything.
- If there is no relevant information, write:
  "No relevant information available in the case records."

CASE DATA:

{json_data}
"""


# ============================================================
# CASE LOOKUP
# ============================================================

def get_case_by_number(case_number):
    """
    Find a Case ONLY by unique case_number.
    """

    if not case_number:
        raise Http404(
            "Case number is required."
        )

    case_number = case_number.strip()

    try:
        return Case.objects.get(
            case_number__iexact=case_number
        )

    except Case.DoesNotExist:
        raise Http404(
            f"Case '{case_number}' was not found."
        )


# ============================================================
# CASE ANALYSIS ENDPOINT
# ============================================================

class AIDocumentAnalyzeView(APIView):

    permission_classes = [
        IsStaffOrAdmin
    ]

    def post(self, request, case_number):

        try:
            case = get_case_by_number(
                case_number
            )

        except Http404 as error:
            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:

            case_data = collect_case_data(
                case
            )

            prompt = build_analysis_prompt(
                case_data
            )

            result = ask_ollama(
                prompt
            )

        except RuntimeError as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as error:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Unable to collect case data: "
                        f"{error}"
                    ),
                    "data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Complete case analysis "
                    "generated successfully."
                ),
                "data": {
                    "case_number":
                        case.case_number,
                    "analysis":
                        result,
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# CASE SUMMARY ENDPOINT
# ============================================================

class AIDocumentSummarizeView(APIView):

    permission_classes = [
        IsStaffOrAdmin
    ]

    def post(self, request, case_number):

        try:
            case = get_case_by_number(
                case_number
            )

        except Http404 as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:

            case_data = collect_case_data(
                case
            )

            prompt = build_summary_prompt(
                case_data
            )

            result = ask_ollama(
                prompt
            )

        except RuntimeError as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as error:

            return Response(
                {
                    "success": False,
                    "message": (
                        "Unable to collect case data: "
                        f"{error}"
                    ),
                    "data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": (
                    "Complete case summary "
                    "generated successfully."
                ),
                "data": {
                    "case_number":
                        case.case_number,
                    "summary":
                        result,
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# OLD TEXT ANALYSIS ENDPOINT
# ============================================================

class AIAnalyzeView(APIView):

    permission_classes = [
        IsStaffOrAdmin
    ]

    def post(self, request):

        serializer = AIRequestSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        text = serializer.validated_data[
            "text"
        ]

        prompt = f"""
You are an AI assistant for a Police and Investigation
Document Management System.

Analyze the following text.

IMPORTANT:

- Analyze only the supplied text.
- Do not invent information.
- Do not assume missing information.
- Keep names, dates and locations when available.
- Clearly distinguish facts from allegations.

Return ONLY plain text.

Do NOT return JSON.
Do NOT use code fences.

Provide:

1. Key Facts
2. Important People
3. Important Dates
4. Locations
5. Evidence Mentioned
6. Potential Risks or Inconsistencies
7. Important Observations

If information is unavailable, write:
"Not available".

TEXT:

{text}
"""

        try:

            result = ask_ollama(
                prompt
            )

        except RuntimeError as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "success": True,
                "message":
                    "AI analysis completed.",
                "data": {
                    "analysis":
                        result,
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# OLD TEXT SUMMARY ENDPOINT
# ============================================================

class AISummarizeView(APIView):

    permission_classes = [
        IsStaffOrAdmin
    ]

    def post(self, request):

        serializer = AIRequestSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        text = serializer.validated_data[
            "text"
        ]

        prompt = f"""
You are an AI assistant for a Police and Investigation
Document Management System.

Summarize the following document.

Requirements:

- Keep important facts.
- Keep names, dates and locations.
- Do not invent information.
- Remove unnecessary repetition.
- Make the summary clear and professional.
- Analyze only the supplied text.

Return ONLY plain text.

Do NOT return JSON.
Do NOT use code fences.
Do NOT add unnecessary introduction or conclusion.

TEXT:

{text}
"""

        try:

            result = ask_ollama(
                prompt
            )

        except RuntimeError as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "success": True,
                "message":
                    "Document summary generated.",
                "data": {
                    "summary":
                        result,
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# CLASSIFICATION
# ============================================================

class AIClassifyView(APIView):

    permission_classes = [
        IsStaffOrAdmin
    ]

    def post(self, request):

        serializer = AIRequestSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        text = serializer.validated_data[
            "text"
        ]

        prompt = f"""
You are an AI classification assistant for a Police
and Investigation Document Management System.

Classify the following document.

Possible categories:

FIR
POLICE_REPORT
INVESTIGATION_REPORT
LEGAL
COURT
EVIDENCE
COMPLAINT
GENERAL
OTHER

Return ONLY the category name.

Do not return JSON.
Do not add explanation.
Do not use Markdown.
Do not invent information.

TEXT:

{text}
"""

        try:

            result = ask_ollama(
                prompt
            )

        except RuntimeError as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        classification = (
            result.strip().upper()
        )

        allowed_categories = {
            "FIR",
            "POLICE_REPORT",
            "INVESTIGATION_REPORT",
            "LEGAL",
            "COURT",
            "EVIDENCE",
            "COMPLAINT",
            "GENERAL",
            "OTHER",
        }

        if classification not in allowed_categories:
            classification = "OTHER"

        return Response(
            {
                "success": True,
                "message":
                    "Document classification completed.",
                "data": {
                    "classification":
                        classification,
                },
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# EXTRACTION
# ============================================================

class AIExtractView(APIView):

    permission_classes = [
        IsStaffOrAdmin
    ]

    def post(self, request):

        serializer = AIRequestSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        text = serializer.validated_data[
            "text"
        ]

        prompt = f"""
You are an information extraction assistant for a Police
and Investigation Document Management System.

Extract information from the text.

Return valid JSON with exactly these fields:

{{
    "people": [],
    "dates": [],
    "locations": [],
    "case_numbers": [],
    "phone_numbers": [],
    "organizations": [],
    "evidence": []
}}

Rules:

- Only extract explicitly present information.
- Do not invent.
- Use empty arrays when unavailable.
- Return JSON only.
- Do not use Markdown code fences.

TEXT:

{text}
"""

        try:

            result = ask_ollama(
                prompt
            )

        except RuntimeError as error:

            return Response(
                {
                    "success": False,
                    "message": str(error),
                    "data": None,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:

            extracted_data = json.loads(
                result
            )

        except json.JSONDecodeError:

            extracted_data = {
                "raw_response":
                    result,
            }

        return Response(
            {
                "success": True,
                "message":
                    "Information extraction completed.",
                "data":
                    extracted_data,
            },
            status=status.HTTP_200_OK,
        )