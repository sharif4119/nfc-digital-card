from django.urls import path

from .views import (
    cancel_payment,
    fail_payment,
    initiate_payment,
    payment_ipn,
    payment_success,
)


urlpatterns = [
    path(
        "payment/<int:order_id>/",
        initiate_payment,
        name="initiate_payment",
    ),

    path(
        "payment/success/",
        payment_success,
        name="payment_success",
    ),

    path(
        "payment/fail/",
        fail_payment,
        name="payment_fail",
    ),

    path(
        "payment/cancel/",
        cancel_payment,
        name="payment_cancel",
    ),

    path(
        "payment/ipn/",
        payment_ipn,
        name="payment_ipn",
    ),
]