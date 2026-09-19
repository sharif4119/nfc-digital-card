from django.contrib import admin

from .models import NFCCard


@admin.register(NFCCard)
class NFCCardAdmin(admin.ModelAdmin):
    list_display = [
        "card_uid",
        "owner",
        "status",
        "public_token",
        "created_at",
    ]

    list_filter = [
        "status",
    ]

    search_fields = [
        "card_uid",
        "public_token",
        "owner__username",
        "owner__email",
    ]

    readonly_fields = [
        "public_token",
        "created_at",
        "activated_at",
    ]