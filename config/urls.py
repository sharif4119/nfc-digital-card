from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),

    path("", include("accounts.urls")),
    path("", include("payments.urls")),

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
    
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )