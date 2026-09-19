from django.urls import path

from .views import dashboard_view, register_view


urlpatterns = [
    path("register/", register_view, name="register"),
    path("dashboard/", dashboard_view, name="dashboard"),
]