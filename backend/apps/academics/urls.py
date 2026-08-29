from rest_framework.routers import DefaultRouter

from apps.academics.views import (
    AcademicYearViewSet,
    ClassSectionViewSet,
    SchoolClassViewSet,
    SectionViewSet,
    SubjectViewSet,
)

router = DefaultRouter()
router.register("academic-years", AcademicYearViewSet, basename="academic-year")
router.register("classes", SchoolClassViewSet, basename="class")
router.register("sections", SectionViewSet, basename="section")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("class-sections", ClassSectionViewSet, basename="class-section")

urlpatterns = router.urls
