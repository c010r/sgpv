from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import HealthcheckView
from users.auth_views import LoginAPIView, LogoutAPIView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", HealthcheckView.as_view(), name="healthz"),
    path("api/token/", LoginAPIView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/logout/", LogoutAPIView.as_view(), name="logout"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include("users.urls")),
    path("api/", include("settings_app.urls")),
    path("api/", include("inventory.urls")),
    path("api/", include("sales.urls")),
    path("api/", include("guests.urls")),
    path("api/", include("reports.urls")),
]
