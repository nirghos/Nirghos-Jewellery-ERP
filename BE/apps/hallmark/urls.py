from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CentreViewSet, HuidSearch, RequestViewSet

router = DefaultRouter()
router.register("hallmark/centres", CentreViewSet, basename="ahc")
router.register("hallmark/requests", RequestViewSet, basename="hallmark")
urlpatterns = [path("hallmark/huid/", HuidSearch.as_view())] + router.urls
