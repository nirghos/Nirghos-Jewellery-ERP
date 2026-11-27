from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

api = [
    path("auth/login/", TokenObtainPairView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("", include("apps.accounts.urls")),
    path("", include("apps.companies.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.suppliers.urls")),
    path("", include("apps.products.urls")),
    path("", include("apps.sales.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.accounting.urls")),
    path("", include("apps.purchases.urls")),
    path("", include("apps.old_gold.urls")),
    path("", include("apps.karigars.urls")),
    path("", include("apps.manufacturing.urls")),
    path("", include("apps.repairs.urls")),
    path("", include("apps.diamonds.urls")),
    path("", include("apps.hallmark.urls")),
    path("", include("apps.schemes.urls")),
    path("", include("apps.hr.urls")),
    path("", include("apps.gst.urls")),
    path("", include("apps.reports.urls")),
]
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
