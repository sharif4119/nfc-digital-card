from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

from products.models import Product

from .forms import OrderForm
from .models import Order, CardAllocation
from profiles.models import BusinessProfile


@login_required
def create_order(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True,
    )

    if request.method == "POST":
        form = OrderForm(request.POST, product=product)

        if form.is_valid():
            business = None
            if product.card_category == "BUSINESS":
                business = BusinessProfile.objects.filter(owner=request.user).first()
                if business is None:
                    form.add_error(None, "Create your business profile before ordering a business card.")
            if form.errors:
                return render(request, "orders/create_order.html", {"form": form, "product": product, "business_profile": business})
            order = form.save(commit=False)

            order.user = request.user
            order.product = product
            order.quantity = form.cleaned_data.get("quantity") or 1
            order.business_order_type = form.cleaned_data.get("business_order_type") or ""
            order.business_profile = business
            order.card_category = product.card_category
            order.offline_contact_print = True
            order.price = product.price * order.quantity
            order.payment_status = "UNPAID"
            order.order_status = "PENDING"

            with transaction.atomic():
                order.save()
                CardAllocation.objects.bulk_create([
                    CardAllocation(order=order, position=position)
                    for position in range(1, order.quantity + 1)
                ])

            messages.success(
                request,
                (
                    "Order submitted successfully. Payment and confirmation "
                    "will be handled by the seller."
                ),
            )

            return redirect(
                "order_detail",
                order_id=order.id,
            )

    else:
        profile = getattr(request.user, "profile", None)
        initial = {
            "customer_name": (
                (
                    profile.full_name
                    or profile.display_username
                    or request.user.username
                )
                if profile
                else request.user.username
            ),
            "phone": (
                profile.phone
                if profile
                else ""
            ),
        }

        form = OrderForm(initial=initial, product=product)

    return render(
        request,
        "orders/create_order.html",
        {
            "form": form,
            "product": product,
            "business_profile": BusinessProfile.objects.filter(owner=request.user).first(),
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
            "allocations": order.allocations.select_related("card", "representative"),
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
