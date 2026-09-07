from django.urls import path

from .views import (
    AIAnalyzeView,
    AISummarizeView,
    AIClassifyView,
    AIExtractView,
    AIDocumentAnalyzeView,
    AIDocumentSummarizeView,
)


urlpatterns = [

    # ========================================================
    # CASE NUMBER BASED AI
    # ========================================================

    # Example:
    # POST /api/ai/documents/CS121/analyze/

    path(
        "documents/<str:case_number>/analyze/",
        AIDocumentAnalyzeView.as_view(),
        name="ai-case-analyze",
    ),

    # Example:
    # POST /api/ai/documents/CS121/summarize/

    path(
        "documents/<str:case_number>/summarize/",
        AIDocumentSummarizeView.as_view(),
        name="ai-case-summarize",
    ),


    # ========================================================
    # OLD TEXT BASED AI ENDPOINTS
    # ========================================================

    path(
        "analyze/",
        AIAnalyzeView.as_view(),
        name="ai-analyze",
    ),

    path(
        "summarize/",
        AISummarizeView.as_view(),
        name="ai-summarize",
    ),

    path(
        "classify/",
        AIClassifyView.as_view(),
        name="ai-classify",
    ),

    path(
        "extract/",
        AIExtractView.as_view(),
        name="ai-extract",
    ),
]
