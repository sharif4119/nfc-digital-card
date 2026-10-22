from django.urls import path

from .views import edit_profile, profile_preview, business_edit, business_cards, business_profile_preview, representative_edit


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

    path(
        "preview/",
        profile_preview,
        name="profile_preview",
    ),
]
