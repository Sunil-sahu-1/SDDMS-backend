from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InvestigationViewSet, WitnessStatementViewSet

router = DefaultRouter()

router.register(
    "investigations",
    InvestigationViewSet,
    basename="investigation",
)

router.register(
    "witness-statements",
    WitnessStatementViewSet,
    basename="witness-statement",
)

urlpatterns = [
    path("", include(router.urls)),
]