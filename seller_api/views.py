from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from cards.models import NFCCard
from orders.models import Order

from .serializers import NFCCardSerializer, OrderSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def seller_login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(
        username=username,
        password=password,
    )

    if not user:
        return Response(
            {"detail": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_staff:
        return Response(
            {"detail": "Seller access required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    token, _ = Token.objects.get_or_create(
        user=user
    )

    return Response(
        {
            "token": token.key,
            "username": user.username,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def dashboard(request):
    return Response(
        {
            "pending_orders": Order.objects.filter(
                order_status="PENDING"
            ).count(),

            "available_cards": NFCCard.objects.filter(
                status="UNASSIGNED"
            ).count(),

            "assigned_cards": NFCCard.objects.filter(
                status="ASSIGNED"
            ).count(),

            "programmed_cards": NFCCard.objects.filter(
                status="PROGRAMMED"
            ).count(),

            "active_cards": NFCCard.objects.filter(
                status="ACTIVE"
            ).count(),
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def order_list(request):
    orders = Order.objects.select_related(
        "user",
        "product",
        "assigned_card",
    ).order_by("-created_at")

    return Response(
        OrderSerializer(
            orders,
            many=True,
            context={"request": request},
        ).data
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related(
            "user",
            "product",
            "assigned_card",
        ),
        id=order_id,
    )

    return Response(
        OrderSerializer(
            order,
            context={"request": request},
        ).data
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def available_cards(request):
    cards = NFCCard.objects.filter(
        status="UNASSIGNED",
        owner__isnull=True,
    ).order_by("card_uid")

    return Response(
        NFCCardSerializer(
            cards,
            many=True,
            context={"request": request},
        ).data
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def assign_card(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
    )

    if order.assigned_card:
        return Response(
            {"detail": "Order already has a card."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    card_id = request.data.get("card_id")

    card = get_object_or_404(
        NFCCard,
        id=card_id,
        status="UNASSIGNED",
        owner__isnull=True,
    )

    existing_card = NFCCard.objects.filter(
        owner=order.user,
    ).exclude(
        status="INACTIVE",
    ).exists()

    if existing_card:
        return Response(
            {
                "detail": (
                    "Customer already has an NFC card."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    card.owner = order.user
    card.status = "ASSIGNED"
    card.programmed_at = None
    card.programmed_by = None
    card.activated_at = None
    card.save()

    order.assigned_card = card
    order.order_status = "CARD_ASSIGNED"

    order.save(
        update_fields=[
            "assigned_card",
            "order_status",
        ]
    )

    return Response(
        OrderSerializer(
            order,
            context={"request": request},
        ).data
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def card_detail(request, card_id):
    card = get_object_or_404(
        NFCCard,
        id=card_id,
    )

    return Response(
        NFCCardSerializer(
            card,
            context={"request": request},
        ).data
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def mark_programmed(request, card_id):
    card = get_object_or_404(
        NFCCard,
        id=card_id,
    )

    if card.status != "ASSIGNED":
        return Response(
            {
                "detail": (
                    "Card must be assigned first."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    card.status = "PROGRAMMED"
    card.programmed_at = timezone.now()
    card.programmed_by = request.user

    card.save(
        update_fields=[
            "status",
            "programmed_at",
            "programmed_by",
        ]
    )

    return Response(
        NFCCardSerializer(
            card,
            context={"request": request},
        ).data
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def activate_card(request, card_id):
    card = get_object_or_404(
        NFCCard,
        id=card_id,
    )

    if card.status != "PROGRAMMED":
        return Response(
            {
                "detail": (
                    "Card must be programmed first."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    card.status = "ACTIVE"
    card.activated_at = timezone.now()

    card.save(
        update_fields=[
            "status",
            "activated_at",
        ]
    )

    return Response(
        NFCCardSerializer(
            card,
            context={"request": request},
        ).data
    )