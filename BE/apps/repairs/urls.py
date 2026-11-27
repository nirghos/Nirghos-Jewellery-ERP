from rest_framework.routers import DefaultRouter
from .views import RepairViewSet

router = DefaultRouter()
router.register("repairs", RepairViewSet, basename="repair")
urlpatterns = router.urls
