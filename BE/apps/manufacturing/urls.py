from rest_framework.routers import DefaultRouter
from .views import DesignViewSet, OrderViewSet

router = DefaultRouter()
router.register("manufacturing/designs", DesignViewSet, basename="design")
router.register("manufacturing/orders", OrderViewSet, basename="prodorder")
urlpatterns = router.urls
