from django.urls import path
from .views import OverviewView

urlpatterns = [path("dashboard/overview/", OverviewView.as_view())]
