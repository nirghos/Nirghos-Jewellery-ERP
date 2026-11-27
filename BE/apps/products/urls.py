from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, RateViewSet

router = DefaultRouter()
router.register("products/categories", CategoryViewSet, basename="category")
router.register("products/rates", RateViewSet, basename="rate")
router.register("products", ProductViewSet, basename="product")
urlpatterns = router.urls
