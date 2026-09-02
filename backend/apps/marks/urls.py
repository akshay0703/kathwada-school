from rest_framework.routers import DefaultRouter

from apps.marks.views import MarkViewSet

router = DefaultRouter()
router.register("marks", MarkViewSet, basename="mark")

urlpatterns = router.urls
