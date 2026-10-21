from django.contrib.auth import authenticate
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.utils import timezone

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from cards.models import NFCCard
from orders.models import Order, CardAllocation

from .print_design import build_card_print_pdf
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
    ).prefetch_related(Prefetch("allocations", queryset=CardAllocation.objects.select_related("card", "representative"))).order_by("-created_at")

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
        ).prefetch_related(Prefetch("allocations", queryset=CardAllocation.objects.select_related("card", "representative"))),
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

    if order.quantity != 1:
        return Response({"detail": "Use individual allocations for multiple-card orders."}, status=400)

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

    if existing_card and not order.business_profile_id:
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
    card.business_profile = order.business_profile
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
    allocation, _ = CardAllocation.objects.get_or_create(order=order, position=1)
    allocation.card = card
    allocation.save(update_fields=["card"])
    if allocation.representative_id:
        card.representative = allocation.representative
        card.save(update_fields=["representative"])

    return Response(
        OrderSerializer(
            order,
            context={"request": request},
        ).data
    )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def prepare_card(request, order_id):
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().select_related(
                "user",
                "product",
                "assigned_card",
            ),
            id=order_id,
        )

        if order.quantity != 1:
            return Response(
                {"detail": "Use the allocation preparation endpoint for each card in a multiple-card order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Returning the existing assignment makes seller-app retries safe.
        if order.assigned_card_id:
            return Response(
                OrderSerializer(
                    order,
                    context={"request": request},
                ).data
            )

        if order.business_profile_id and order.business_profile.owner_id != order.user_id:
            return Response({"detail": "The business profile must belong to the purchaser."}, status=400)

        conflicting_card = (
            NFCCard.objects.select_for_update()
            .filter(owner=order.user)
            .exclude(status="INACTIVE")
            .first()
        )

        if conflicting_card and not order.business_profile_id:
            return Response(
                {
                    "detail": (
                        "This customer already has a non-inactive NFC card "
                        "assigned to another order."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        card = NFCCard.create_with_generated_uid(
            owner=order.user,
            status="ASSIGNED",
            business_profile=order.business_profile,
            programmed_at=None,
            programmed_by=None,
            activated_at=None,
        )

        order.assigned_card = card
        order.order_status = "CARD_ASSIGNED"
        order.save(
            update_fields=[
                "assigned_card",
                "order_status",
            ]
        )
        allocation, _ = CardAllocation.objects.get_or_create(order=order, position=1)
        allocation.card = card
        allocation.save(update_fields=["card"])
        if allocation.representative_id:
            card.representative = allocation.representative
            card.save(update_fields=["representative"])

        return Response(
            OrderSerializer(
                order,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([IsAdminUser])
def prepare_allocation(request, order_id, allocation_id):
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update().select_related("user", "product", "business_profile", "assigned_card"),
            pk=order_id,
        )
        allocation = get_object_or_404(
            CardAllocation.objects.select_for_update().select_related("card", "representative"),
            pk=allocation_id, order=order,
        )
        if allocation.card_id:
            return Response(OrderSerializer(order, context={"request": request}).data)
        if allocation.position == 1 and order.assigned_card_id:
            allocation.card = order.assigned_card
            allocation.save(update_fields=["card"])
            return Response(OrderSerializer(order, context={"request": request}).data)
        if order.card_category == "BUSINESS":
            if not order.business_profile_id or order.business_profile.owner_id != order.user_id:
                return Response({"detail": "The order needs a business profile owned by the purchaser."}, status=400)
            if allocation.representative_id and allocation.representative.business_id != order.business_profile_id:
                return Response({"detail": "Representative does not belong to this business."}, status=400)
        elif order.quantity != 1:
            return Response({"detail": "Personal orders support one card."}, status=400)
        card = NFCCard.create_with_generated_uid(
            owner=order.user, status="ASSIGNED",
            business_profile=order.business_profile,
            representative=allocation.representative,
            programmed_at=None, programmed_by=None, activated_at=None,
        )
        allocation.card = card
        allocation.save(update_fields=["card"])
        if not order.assigned_card_id:
            order.assigned_card = card
        order.order_status = "CARD_ASSIGNED"
        order.save(update_fields=["assigned_card", "order_status"])
        return Response(OrderSerializer(order, context={"request": request}).data)


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


@api_view(["GET"])
@permission_classes([IsAdminUser])
def card_print_pdf(request, card_id):
    card = get_object_or_404(
        NFCCard,
        id=card_id,
        status__in=[
            "ASSIGNED",
            "PROGRAMMED",
            "ACTIVE",
        ],
    )
    pdf = build_card_print_pdf(card)
    filename = f"NexTap-{card.card_uid}-front-back.pdf"
    response = HttpResponse(
        pdf,
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )
    return response


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
