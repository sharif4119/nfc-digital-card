from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "image_preview",
        "name",
        "price",
        "is_available",
        "card_category",
        "created_at",
        "edit_details",
    ]

    # Keep legacy database values intact, but do not expose dimensions in the
    # product creation/editing interface.
    exclude = ("card_width_mm", "card_height_mm")

    list_filter = [
        "is_available",
    ]

    search_fields = [
        "name",
        "description",
    ]

    list_filter = ("card_category", "is_available", "created_at")
    list_per_page = 25

    @admin.display(description="Image")
    def image_preview(self, obj):
        if not obj.image:
            return "—"
        try:
            if not obj.image.storage.exists(obj.image.name):
                return "—"
            image_url = obj.image.url
        except (OSError, ValueError):
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width:56px;height:42px;object-fit:cover;border-radius:5px">',
            image_url,
        )

    @admin.display(description="Actions")
    def edit_details(self, obj):
        url = reverse("admin:products_product_change", args=(obj.pk,))
        return format_html('<a class="nxtap-admin-edit-button" href="{}">Edit details</a>', url)
