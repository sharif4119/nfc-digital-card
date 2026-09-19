from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product

from .forms import OrderForm
from .models import Order


@login_required
def create_order(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True,
    )

    if request.method == "POST":
        form = OrderForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)

            order.user = request.user
            order.product = product
            order.quantity = 1
            order.price = product.price

            order.save()

            return redirect(
                "order_detail",
                order_id=order.id,
            )

    else:
        initial = {
            "customer_name": (
                request.user.profile.full_name
                if hasattr(request.user, "profile")
                else request.user.username
            ),
            "phone": (
                request.user.profile.phone
                if hasattr(request.user, "profile")
                else ""
            ),
        }

        form = OrderForm(initial=initial)

    return render(
        request,
        "orders/create_order.html",
        {
            "form": form,
            "product": product,
        },
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
    )

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
        },
    )


@login_required
def order_list(request):
    orders = Order.objects.filter(
        user=request.user,
    ).order_by("-created_at")

    return render(
        request,
        "orders/order_list.html",
        {
            "orders": orders,
        },
    )
