"""Customer-safe display references for orders."""

from .models import Order


def customer_order_number_map(user):
    """Map a user's orders to stable, account-local chronological numbers."""
    order_ids = Order.objects.filter(user=user).order_by("created_at", "pk").values_list("pk", flat=True)
    return {order_id: number for number, order_id in enumerate(order_ids, start=1)}


def add_customer_order_numbers(orders, user):
    """Attach non-persistent customer order numbers to loaded order objects."""
    numbers = customer_order_number_map(user)
    orders = list(orders)
    for order in orders:
        order.customer_order_number = numbers.get(order.pk, "")
    return orders


def get_customer_order_number(order):
    return customer_order_number_map(order.user).get(order.pk, "")
