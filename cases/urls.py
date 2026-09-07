from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CaseViewSet


router = DefaultRouter()

router.register(
    "",
    CaseViewSet,
    basename="case",
)

urlpatterns = router.urls