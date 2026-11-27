from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PurchaseViewSet, SupplierLedger, SupplierPaymentViewSet

router = DefaultRouter()
router.register("purchases/payments", SupplierPaymentViewSet, basename="supplier-payment")
router.register("purchases/invoices", PurchaseViewSet, basename="purchase")
urlpatterns = [path("purchases/ledger/", SupplierLedger.as_view())] + router.urls
