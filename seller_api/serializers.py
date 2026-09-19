from rest_framework import serializers

from cards.models import NFCCard
from orders.models import Order


class NFCCardSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True,
    )

    public_url = serializers.SerializerMethodField()

    class Meta:
        model = NFCCard
        fields = [
            "id",
            "card_uid",
            "public_token",
            "public_url",
            "status",
            "owner",
            "owner_username",
            "programmed_at",
            "activated_at",
        ]

        read_only_fields = fields

    def get_public_url(self, obj):
        request = self.context.get("request")

        path = f"/c/{obj.public_token}/"

        if request:
            return request.build_absolute_uri(path)

        return path


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