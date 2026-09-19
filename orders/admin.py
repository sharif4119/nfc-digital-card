from django.contrib import admin


from cards.models import NFCCard
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
        "assigned_card",
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
        "assigned_card__card_uid",
    ]

    readonly_fields = [
        "created_at",
    ]

    fieldsets = [
        (
            "Order",
            {
                "fields": [
                    "user",
                    "product",
                    "quantity",
                    "price",
                ]
            },
        ),
        (
            "Customer",
            {
                "fields": [
                    "customer_name",
                    "phone",
                    "address",
                    "city",
                ]
            },
        ),
        (
            "Status",
            {
                "fields": [
                    "payment_status",
                    "order_status",
                    "assigned_card",
                ]
            },
        ),
        (
            "System",
            {
                "fields": [
                    "created_at",
                ]
            },
        ),
    ]

    def formfield_for_foreignkey(
        self,
        db_field,
        request,
        **kwargs,
    ):
        if db_field.name == "assigned_card":
            object_id = (
                request.resolver_match.kwargs.get(
                    "object_id"
                )
                if request.resolver_match
                else None
            )

            queryset = NFCCard.objects.filter(
                owner__isnull=True,
                status="UNASSIGNED",
            )

            if object_id:
                order = Order.objects.filter(
                    pk=object_id
                ).first()

                if order and order.assigned_card:
                    queryset = (
                        queryset
                        | NFCCard.objects.filter(
                            pk=order.assigned_card.pk
                        )
                    )

            kwargs["queryset"] = queryset.distinct()

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs,
        )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        previous_card = None

        if obj.pk:
            previous_order = Order.objects.filter(
                pk=obj.pk
            ).first()

            if previous_order:
                previous_card = (
                    previous_order.assigned_card
                )

        super().save_model(
            request,
            obj,
            form,
            change,
        )

        new_card = obj.assigned_card

        # Release old card if assignment changed or removed.
        if previous_card and previous_card != new_card:
            previous_card.owner = None
            previous_card.status = "UNASSIGNED"
            previous_card.programmed_at = None
            previous_card.programmed_by = None
            previous_card.activated_at = None

            previous_card.save(
                update_fields=[
                    "owner",
                    "status",
                    "programmed_at",
                    "programmed_by",
                    "activated_at",
                ]
            )

        # Newly assigned card should only become ASSIGNED.
        if new_card:
            new_card.owner = obj.user
            new_card.status = "ASSIGNED"
            new_card.programmed_at = None
            new_card.programmed_by = None
            new_card.activated_at = None

            new_card.save(
                update_fields=[
                    "owner",
                    "status",
                    "programmed_at",
                    "programmed_by",
                    "activated_at",
                ]
            )

            if obj.order_status != "CARD_ASSIGNED":
                obj.order_status = "CARD_ASSIGNED"

                obj.save(
                    update_fields=[
                        "order_status",
                    ]
                )

        # Card assignment removed completely.
        elif (
            previous_card
            and obj.order_status == "CARD_ASSIGNED"
        ):
            obj.order_status = (
                "PAID"
                if obj.payment_status == "PAID"
                else "PENDING"
            )

            obj.save(
                update_fields=[
                    "order_status",
                ]
            )
            