from django.urls import include, path

from apps.common.views import health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.academics.urls")),
]
