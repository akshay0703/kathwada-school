from rest_framework.routers import DefaultRouter

from apps.library.views import BookIssueViewSet, BookViewSet

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("book-issues", BookIssueViewSet, basename="book-issue")

urlpatterns = router.urls
