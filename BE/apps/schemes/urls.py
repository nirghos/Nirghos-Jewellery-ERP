from rest_framework.routers import DefaultRouter
from .views import MemberViewSet, PlanViewSet

router = DefaultRouter()
router.register("schemes/plans", PlanViewSet, basename="scheme-plan")
router.register("schemes/members", MemberViewSet, basename="scheme-member")
urlpatterns = router.urls
