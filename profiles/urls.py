from django.urls import path

from .views import edit_profile, profile_preview


urlpatterns = [
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