from rest_framework.routers import DefaultRouter

from apps.academics.views import AcademicYearViewSet

router = DefaultRouter()
router.register("academic-years", AcademicYearViewSet, basename="academic-year")

urlpatterns = router.urls
