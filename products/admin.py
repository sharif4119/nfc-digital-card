from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "price",
        "is_available",
        "card_category",
        "created_at",
    ]

    # Keep legacy database values intact, but do not expose dimensions in the
    # product creation/editing interface.
    exclude = ("card_width_mm", "card_height_mm")

    list_filter = [
        "is_available",
    ]

    search_fields = [
        "name",
    ]
