from django.urls import path

from .views import (
    card_qr_view,
    download_vcard,
    offline_contact_qr,
    public_card_view,
)


urlpatterns = [
    path("c/<str:token>/offline-qr/", offline_contact_qr, name="offline_contact_qr"),
    path(
        "c/<str:token>/",
        public_card_view,
        name="public_card",
    ),

    path(
        "c/<str:token>/qr/",
        card_qr_view,
        name="card_qr",
    ),

    path(
        "c/<str:token>/contact/",
        download_vcard,
        name="download_vcard",
    ),
]
