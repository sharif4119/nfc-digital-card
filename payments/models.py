from django.db import models

from orders.models import Order


class Payment(models.Model):
    STATUS_CHOICES = [
        ("INITIATED", "Initiated"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    transaction_id = models.CharField(
        max_length=50,
        unique=True,
    )

    validation_id = models.CharField(
        max_length=100,
        blank=True,
    )

    session_key = models.CharField(
        max_length=100,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="INITIATED",
    )

    payment_method = models.CharField(
        max_length=100,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"