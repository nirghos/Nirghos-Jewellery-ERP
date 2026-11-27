from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet

router = DefaultRouter()
router.register("sales/invoices", InvoiceViewSet, basename="invoice")
urlpatterns = router.urls
