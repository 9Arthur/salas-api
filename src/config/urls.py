from django.contrib import admin
from django.urls import include, path

from config.views import healthz

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthz),
    path("api/auth/", include("users.urls")),
    path("api/", include("reservas.urls")),
]
