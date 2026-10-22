from django.urls import path

from .views import edit_profile, profile_preview, download_profile_vcard, business_edit, business_cards, business_profile_preview, representative_edit


urlpatterns = [
    path("business/", business_edit, name="business_edit"),
    path("business/preview/", business_profile_preview, name="business_profile_preview"),
    path("business/cards/", business_cards, name="business_cards"),
    path("business/cards/<int:allocation_id>/representative/", representative_edit, name="representative_edit"),
    path(
        "edit/",
        edit_profile,
        name="edit_profile",
    ),
    path("contact/", download_profile_vcard, name="download_profile_vcard"),

    path(
        "preview/",
        profile_preview,
        name="profile_preview",
    ),
]
