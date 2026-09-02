from rest_framework.routers import DefaultRouter

from apps.attendance.views import AttendanceRecordViewSet

router = DefaultRouter()
router.register("attendance", AttendanceRecordViewSet, basename="attendance-record")

urlpatterns = router.urls
