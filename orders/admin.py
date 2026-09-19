from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "product",
        "price",
        "payment_status",
        "order_status",
        "created_at",
    ]

    list_filter = [
        "payment_status",
        "order_status",
    ]

    search_fields = [
        "customer_name",
        "phone",
        "user__username",
    ]