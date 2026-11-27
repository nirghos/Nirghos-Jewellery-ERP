from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, me

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
urlpatterns = [path("auth/me/", me)] + router.urls
