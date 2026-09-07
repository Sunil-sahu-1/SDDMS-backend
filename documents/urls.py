from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet
from .file_views import view_document

router = DefaultRouter()

router.register(
    "",
    DocumentViewSet,
    basename="document",
)

urlpatterns = [
    path(
        "<int:pk>/view/",
        view_document,
        name="document-view",
    ),
    path(
        "",
        include(router.urls),
    ),
]
