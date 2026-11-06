from django.db.models import Count, Q, Sum
from django.urls import reverse


def admin_dashboard(request):
    """Add operational summaries only to the Django admin index request."""
    match = getattr(request, "resolver_match", None)
    if (
        not request.user.is_authenticated
        or not request.user.is_staff
        or not match
        or match.url_name != "index"
        or match.namespace != "admin"
    ):
        return {}

    from cards.models import NFCCard
    from orders.models import Order
    from products.models import Product
    from django.contrib.auth import get_user_model

    User = get_user_model()
    card_products = list(Product.objects.filter(is_available=True).order_by("id"))
    for product in card_products:
        try:
            product.admin_image_url = (
                product.image.url
                if product.image and product.image.storage.exists(product.image.name)
                else ""
            )
        except (OSError, ValueError):
            product.admin_image_url = ""

    paid_orders = Order.objects.filter(payment_status="PAID")
    status_summary = list(
        Order.objects.values("order_status").annotate(total=Count("id")).order_by("order_status")
    )
    payment_summary = list(
        Order.objects.values("payment_status").annotate(total=Count("id")).order_by("payment_status")
    )
    return {
        "nxtap_admin_stats": {
            "total_orders": Order.objects.count(),
            "total_users": User.objects.count(),
            "available_products": Product.objects.filter(is_available=True).count(),
            "cards_sold": paid_orders.aggregate(total=Sum("quantity"))["total"] or 0,
            "paid_revenue": paid_orders.aggregate(total=Sum("price"))["total"] or 0,
            "pending_orders": Order.objects.filter(
                Q(order_status__in=("PENDING", "PROCESSING"))
                | (Q(payment_status="UNPAID") & ~Q(order_status="CANCELLED"))
            ).count(),
            "unassigned_cards": NFCCard.objects.filter(status="UNASSIGNED").count(),
            "active_cards": NFCCard.objects.filter(status="ACTIVE").count(),
        },
        "nxtap_recent_orders": Order.objects.select_related("user", "product").order_by(
            "-created_at", "-pk"
        )[:6],
        "nxtap_recent_cards": NFCCard.objects.select_related("owner", "business_profile").order_by(
            "-created_at", "-pk"
        )[:6],
        "nxtap_card_products": card_products,
        "nxtap_order_status_summary": status_summary,
        "nxtap_payment_status_summary": payment_summary,
        "nxtap_admin_links": {
            "orders": reverse("admin:orders_order_changelist"),
            "cards": reverse("admin:cards_nfccard_changelist"),
            "users": reverse("admin:auth_user_changelist"),
            "products": reverse("admin:products_product_changelist"),
            "add_product": reverse("admin:products_product_add"),
        },
    }
