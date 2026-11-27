from rest_framework.routers import DefaultRouter
from .views import BatchViewSet, ReceiptViewSet

router = DefaultRouter()
router.register("old-gold/melting", BatchViewSet, basename="melting")
router.register("old-gold", ReceiptViewSet, basename="oldgold")
urlpatterns = router.urls
