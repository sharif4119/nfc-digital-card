from django.contrib.auth.models import User
from django.db import models

from products.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("PROCESSING", "Processing"),
        ("CARD_ASSIGNED", "Card Assigned"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )
    
    assigned_card = models.OneToOneField(
    "cards.NFCCard",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="assigned_order",
    )
    
    quantity = models.PositiveIntegerField(default=1)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    customer_name = models.CharField(max_length=150)

    phone = models.CharField(max_length=30)

    address = models.TextField()

    city = models.CharField(max_length=100)

    payment_status = models.CharField(
        max_length=20,
        default="UNPAID",
    )

    order_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"