from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import BranchViewSet, CompanyView

router = DefaultRouter()
router.register("branches", BranchViewSet, basename="branch")
urlpatterns = [path("company/", CompanyView.as_view())] + router.urls
