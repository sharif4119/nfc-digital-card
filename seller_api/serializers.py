from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from cards.models import NFCCard
from orders.models import Order, CardAllocation


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
    card_category = serializers.SerializerMethodField()
    representative = serializers.SerializerMethodField()

    class Meta:
        model = NFCCard
        fields = [
            "id",
            "card_uid",
            "public_token",
            "public_url",
            "print_pdf_url",
            "card_category",
            "representative",
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

    def get_card_category(self, obj):
        return "BUSINESS" if obj.business_profile_id else "PERSONAL"

    def get_representative(self, obj):
        if not obj.representative_id:
            return None
        rep = obj.representative
        return {"id": rep.id, "name": rep.name, "designation": rep.designation, "phone": rep.phone, "email": rep.email}

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.status not in self.PRINTABLE_STATUSES:
            data.pop("print_pdf_url", None)

        return data


class CardAllocationSerializer(serializers.ModelSerializer):
    card = NFCCardSerializer(read_only=True)
    representative = serializers.SerializerMethodField()

    class Meta:
        model = CardAllocation
        fields = ["id", "position", "representative", "card"]
        read_only_fields = fields

    def get_representative(self, obj):
        if not obj.representative_id:
            return None
        rep = obj.representative
        return {"id": rep.id, "name": rep.name, "designation": rep.designation, "phone": rep.phone, "email": rep.email}


class OrderSerializer(serializers.ModelSerializer):
    prepared_count = serializers.SerializerMethodField()
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
    allocations = CardAllocationSerializer(many=True, read_only=True)

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
            "card_category",
            "business_order_type",
            "quantity",
            "prepared_count",
            "allocations",
            "created_at",
        ]

        read_only_fields = fields

    def get_prepared_count(self, obj):
        return sum(1 for allocation in obj.allocations.all() if allocation.card_id)
