from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from cards.models import NFCCard
from orders.models import Order


class NFCCardSerializer(serializers.ModelSerializer):
    PRINTABLE_STATUSES = {
        "ASSIGNED",
        "PROGRAMMED",
        "ACTIVE",
    }

    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True,
    )

    public_url = serializers.SerializerMethodField()
    print_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = NFCCard
        fields = [
            "id",
            "card_uid",
            "public_token",
            "public_url",
            "print_pdf_url",
            "status",
            "owner",
            "owner_username",
            "programmed_at",
            "activated_at",
        ]

        read_only_fields = fields

    def get_public_url(self, obj):
        return obj.public_url

    def get_print_pdf_url(self, obj):
        path = reverse(
            "seller_api_card_print_pdf",
            kwargs={"card_id": obj.id},
        )
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}" f"{path}"

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.status not in self.PRINTABLE_STATUSES:
            data.pop("print_pdf_url", None)

        return data


class OrderSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    assigned_card = NFCCardSerializer(
        read_only=True,
    )

    class Meta:
        model = Order

        fields = [
            "id",
            "username",
            "customer_name",
            "phone",
            "address",
            "city",
            "product_name",
            "price",
            "payment_status",
            "order_status",
            "assigned_card",
            "created_at",
        ]

        read_only_fields = fields
