from django.urls import path

from .views import (
    create_order,
    customer_order_detail,
    order_detail,
    order_list,
)


urlpatterns = [
    path(
        "order/<int:product_id>/",
        create_order,
        name="create_order",
    ),

    path(
        "orders/",
        order_list,
        name="order_list",
    ),

    path(
        "my-orders/<int:customer_order_number>/",
        customer_order_detail,
        name="customer_order_detail",
    ),

    path(
        "orders/<int:order_id>/",
        order_detail,
        name="order_detail",
    ),
]
