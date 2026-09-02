from rest_framework.routers import DefaultRouter

from apps.exams.views import ExamSubjectViewSet, ExamViewSet

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")
router.register("exam-subjects", ExamSubjectViewSet, basename="exam-subject")

urlpatterns = router.urls
