from rest_framework.routers import DefaultRouter

from apps.people.views import EnrollmentViewSet, StudentViewSet, TeacherAssignmentViewSet, TeacherViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("teachers", TeacherViewSet, basename="teacher")
router.register("teacher-assignments", TeacherAssignmentViewSet, basename="teacher-assignment")

urlpatterns = router.urls
