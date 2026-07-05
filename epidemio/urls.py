"""Configuration des URLs du projet epidemio (SNSE)."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("sanitrax.urls")),
]
