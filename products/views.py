from django.shortcuts import get_object_or_404, render

from .models import Product


def product_list(request):
    products = Product.objects.filter(
        is_available=True,
    ).order_by("id")

    return render(
        request,
        "products/product_list.html",
        {
            "personal_products": products.filter(card_category="PERSONAL"),
            "business_products": products.filter(card_category="BUSINESS"),
        },
    )


def product_detail(request, pk):
    product = get_object_or_404(
        Product,
        pk=pk,
        is_available=True,
    )

    return render(
        request,
        "products/product_detail.html",
        {
            "product": product,
        },
    )
