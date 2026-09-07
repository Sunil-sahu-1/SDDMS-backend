
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include("accounts.urls")),
    path("api/cases/", include("cases.urls")),
    path("api/audit/",include("audit.urls")),
    path("api/evidence/",include("evidence.urls")),
    path("api/investigations/",include("investigations.urls")),
    path("api/", include("complaints.urls")),
    path("api/legal/",include("legal.urls")),
    path("api/documents/",include("documents.urls")),
    path("api/ai/", include("ai.urls")),
    path("api/search/",include("search.urls")),
    path("api/admin/dashboard/",include("dashboard.urls")),
    path("api/notifications/",include("notifications.urls")),
    path("api/dashboard/", include("dashboard.urls")),

    #path("api/witness-statements/",include("witness_statements.urls")),









]
