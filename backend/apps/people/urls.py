from rest_framework.routers import DefaultRouter

from apps.people.views import EnrollmentViewSet, StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")

urlpatterns = router.urls
