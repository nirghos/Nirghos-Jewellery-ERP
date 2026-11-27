from django.urls import path
from .views import ReportList, ReportView

urlpatterns = [path("reports/", ReportList.as_view()), path("reports/<str:name>/", ReportView.as_view())]
