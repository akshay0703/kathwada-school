from rest_framework.routers import DefaultRouter

from apps.fees.views import FeeInvoiceViewSet, FeePaymentViewSet, FeeStructureViewSet

router = DefaultRouter()
router.register("fee-structures", FeeStructureViewSet, basename="fee-structure")
router.register("fee-invoices", FeeInvoiceViewSet, basename="fee-invoice")
router.register("fee-payments", FeePaymentViewSet, basename="fee-payment")

urlpatterns = router.urls
