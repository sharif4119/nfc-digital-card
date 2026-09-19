from django.urls import path

from .views import public_card_view


urlpatterns = [
    path(
        "c/<str:token>/",
        public_card_view,
        name="public_card",
    ),
]