from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_id",
        "order",
        "amount",
        "status",
        "payment_method",
        "created_at",
    ]

    list_filter = [
        "status",
    ]

    search_fields = [
        "transaction_id",
        "order__id",
        "order__user__username",
    ]

    readonly_fields = [
        "transaction_id",
        "validation_id",
        "session_key",
        "created_at",
        "updated_at",
    ]