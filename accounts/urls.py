from django.urls import path

from .views import (
    NexTapLoginView,
    dashboard_view,
    register_view,
)


urlpatterns = [
    path("register/", register_view, name="register"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path(
        "accounts/login/",
        NexTapLoginView.as_view(),
        name="login",
    ),
]
