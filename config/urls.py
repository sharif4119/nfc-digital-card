from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("core.urls")),
    path("", include("accounts.urls")),

    path(
        "accounts/",
        include("django.contrib.auth.urls"),
    ),

    path(
        "profile/",
        include("profiles.urls"),
    ),

    path("", include("cards.urls")),
    path("", include("products.urls")),
    path("", include("orders.urls")),

    path(
        "api/seller/",
        include("seller_api.urls"),
    ),

    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]