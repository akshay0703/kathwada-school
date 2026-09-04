from rest_framework.routers import DefaultRouter

from apps.people.views import (
    EnrollmentViewSet,
    GuardianViewSet,
    StudentGuardianViewSet,
    StudentViewSet,
    TeacherAssignmentViewSet,
    TeacherViewSet,
)

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("teachers", TeacherViewSet, basename="teacher")
router.register("teacher-assignments", TeacherAssignmentViewSet, basename="teacher-assignment")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("student-guardians", StudentGuardianViewSet, basename="student-guardian")

urlpatterns = router.urls
