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
]
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
