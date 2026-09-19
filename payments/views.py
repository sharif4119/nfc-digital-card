import uuid
from decimal import Decimal

import requests

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from orders.models import Order

from .models import Payment


SANDBOX_SESSION_URL = (
    "https://sandbox-gw.sslcommerz.com/"
    "gwprocess/v4/api.php"
)

SANDBOX_VALIDATION_URL = (
    "https://sandbox.sslcommerz.com/"
    "validator/api/validationserverAPI.php"
)


@login_required
def initiate_payment(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
    )

    if order.payment_status == "PAID":
        return redirect(
            "order_detail",
            order_id=order.id,
        )

    transaction_id = (
        f"ORDER{order.id}-"
        f"{uuid.uuid4().hex[:12]}"
    )

    payment, _ = Payment.objects.update_or_create(
        order=order,
        defaults={
            "transaction_id": transaction_id,
            "amount": order.price,
            "status": "INITIATED",
        },
    )

    success_url = request.build_absolute_uri(
        reverse("payment_success")
    )

    fail_url = request.build_absolute_uri(
        reverse("payment_fail")
    )

    cancel_url = request.build_absolute_uri(
        reverse("payment_cancel")
    )

    ipn_url = request.build_absolute_uri(
        reverse("payment_ipn")
    )

    data = {
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,

        "total_amount": str(order.price),
        "currency": "BDT",
        "tran_id": transaction_id,

        "success_url": success_url,
        "fail_url": fail_url,
        "cancel_url": cancel_url,
        "ipn_url": ipn_url,

        "cus_name": order.customer_name,
        "cus_email": request.user.email or "demo@example.com",
        "cus_add1": order.address,
        "cus_city": order.city,
        "cus_country": "Bangladesh",
        "cus_phone": order.phone,

        "shipping_method": "YES",
        "ship_name": order.customer_name,
        "ship_add1": order.address,
        "ship_city": order.city,
        "ship_country": "Bangladesh",

        "product_name": order.product.name,
        "product_category": "NFC Card",
        "product_profile": "physical-goods",
    }

    try:
        response = requests.post(
            SANDBOX_SESSION_URL,
            data=data,
            timeout=20,
        )

        response.raise_for_status()

        result = response.json()

    except (
        requests.RequestException,
        ValueError,
    ):
        return render(
            request,
            "payments/payment_error.html",
            {
                "message": (
                    "Could not connect to the payment gateway."
                )
            },
        )

    if result.get("status") != "SUCCESS":
        return render(
            request,
            "payments/payment_error.html",
            {
                "message": result.get(
                    "failedreason",
                    "Payment session could not be created.",
                )
            },
        )

    payment.session_key = result.get(
        "sessionkey",
        "",
    )

    payment.save(
        update_fields=["session_key"]
    )

    gateway_url = result.get(
        "GatewayPageURL"
    )

    if not gateway_url:
        return render(
            request,
            "payments/payment_error.html",
            {
                "message": (
                    "Payment gateway URL was not returned."
                )
            },
        )

    return redirect(gateway_url)


def validate_sslcommerz_payment(val_id):
    params = {
        "val_id": val_id,
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "format": "json",
    }

    response = requests.get(
        SANDBOX_VALIDATION_URL,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


@csrf_exempt
def payment_success(request):
    if request.method != "POST":
        return HttpResponse(
            "Invalid request.",
            status=400,
        )

    transaction_id = request.POST.get(
        "tran_id"
    )

    validation_id = request.POST.get(
        "val_id"
    )

    if not transaction_id or not validation_id:
        return HttpResponse(
            "Missing payment information.",
            status=400,
        )

    payment = get_object_or_404(
        Payment,
        transaction_id=transaction_id,
    )

    try:
        validation = validate_sslcommerz_payment(
            validation_id
        )

    except (
        requests.RequestException,
        ValueError,
    ):
        return render(
            request,
            "payments/payment_error.html",
            {
                "message": (
                    "Payment verification failed."
                )
            },
        )

    status = validation.get("status")

    validated_transaction = validation.get(
        "tran_id"
    )

    validated_currency = validation.get(
        "currency"
    )

    try:
        validated_amount = Decimal(
            validation.get("amount", "0")
        )
    except Exception:
        validated_amount = Decimal("0")

    valid_status = status in {
        "VALID",
        "VALIDATED",
    }

    if (
        valid_status
        and validated_transaction
        == payment.transaction_id
        and validated_amount
        == payment.amount
        and validated_currency == "BDT"
    ):
        payment.status = "PAID"
        payment.validation_id = validation_id
        payment.payment_method = validation.get(
            "card_type",
            "",
        )

        payment.save()

        order = payment.order
        order.payment_status = "PAID"
        order.order_status = "PAID"

        order.save(
            update_fields=[
                "payment_status",
                "order_status",
            ]
        )

        return render(
            request,
            "payments/payment_success.html",
            {
                "order": order,
                "payment": payment,
            },
        )

    return render(
        request,
        "payments/payment_error.html",
        {
            "message": (
                "The payment could not be verified."
            )
        },
    )


@csrf_exempt
def fail_payment(request):
    transaction_id = request.POST.get(
        "tran_id"
    )

    if transaction_id:
        Payment.objects.filter(
            transaction_id=transaction_id,
        ).update(
            status="FAILED",
        )

    return render(
        request,
        "payments/payment_fail.html",
    )


@csrf_exempt
def cancel_payment(request):
    transaction_id = request.POST.get(
        "tran_id"
    )

    if transaction_id:
        Payment.objects.filter(
            transaction_id=transaction_id,
        ).update(
            status="CANCELLED",
        )

    return render(
        request,
        "payments/payment_cancel.html",
    )


@csrf_exempt
def payment_ipn(request):
    if request.method != "POST":
        return HttpResponse(
            "Invalid request.",
            status=400,
        )

    transaction_id = request.POST.get(
        "tran_id"
    )

    validation_id = request.POST.get(
        "val_id"
    )

    if not transaction_id or not validation_id:
        return HttpResponse(
            "Missing data.",
            status=400,
        )

    payment = Payment.objects.filter(
        transaction_id=transaction_id,
    ).first()

    if not payment:
        return HttpResponse(
            "Payment not found.",
            status=404,
        )

    try:
        validation = validate_sslcommerz_payment(
            validation_id
        )

        validated_amount = Decimal(
            validation.get("amount", "0")
        )

    except Exception:
        return HttpResponse(
            "Validation failed.",
            status=400,
        )

    if (
        validation.get("status")
        in {"VALID", "VALIDATED"}
        and validation.get("tran_id")
        == payment.transaction_id
        and validated_amount
        == payment.amount
        and validation.get("currency")
        == "BDT"
    ):
        payment.status = "PAID"
        payment.validation_id = validation_id
        payment.payment_method = validation.get(
            "card_type",
            "",
        )

        payment.save()

        order = payment.order
        order.payment_status = "PAID"
        order.order_status = "PAID"

        order.save(
            update_fields=[
                "payment_status",
                "order_status",
            ]
        )

        return HttpResponse("Payment verified.")

    return HttpResponse(
        "Invalid payment.",
        status=400,
    )