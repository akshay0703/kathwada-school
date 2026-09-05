from django.urls import include, path

from apps.common.views import health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.academics.urls")),
    path("", include("apps.people.urls")),
    path("", include("apps.attendance.urls")),
    path("", include("apps.exams.urls")),
    path("", include("apps.marks.urls")),
    path("", include("apps.fees.urls")),
    path("", include("apps.library.urls")),
]
