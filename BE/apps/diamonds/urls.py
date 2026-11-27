from rest_framework.routers import DefaultRouter
from .views import StoneViewSet

router = DefaultRouter()
router.register("stones", StoneViewSet, basename="stone")
urlpatterns = router.urls
