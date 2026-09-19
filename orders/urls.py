from django.urls import path

from .views import (
    create_order,
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
        "orders/<int:order_id>/",
        order_detail,
        name="order_detail",
    ),
]