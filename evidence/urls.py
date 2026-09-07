from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EvidenceViewSet
from .file_views import view_evidence

router = DefaultRouter()

router.register(
    r"",
    EvidenceViewSet,
    basename="evidence"
)

urlpatterns = [
    path(
        "<int:pk>/view/",
        view_evidence,
        name="evidence-view",
    ),
    *router.urls,
]
