from rest_framework.routers import DefaultRouter

from .views import (
    LegalReviewViewSet,
    CourtHearingViewSet,
)


router = DefaultRouter()

router.register(
    r"reviews",
    LegalReviewViewSet,
    basename="legal-review",
)

router.register(
    r"hearings",
    CourtHearingViewSet,
    basename="court-hearing",
)

urlpatterns = router.urls
