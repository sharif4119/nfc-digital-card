from django.contrib.auth.models import User
from django.db import models

from products.models import Product


class Order(models.Model):
    BUSINESS_ORDER_TYPES = [("", "Personal / legacy"), ("SINGLE", "Single business card"), ("MULTIPLE", "Multiple business cards")]
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
    business_order_type = models.CharField(max_length=10, choices=BUSINESS_ORDER_TYPES, default="", blank=True)
    card_category = models.CharField(max_length=12, default="PERSONAL")
    card_width_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    card_height_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    offline_contact_print = models.BooleanField(default=False)
    business_profile = models.ForeignKey(
        "profiles.BusinessProfile", on_delete=models.PROTECT, null=True, blank=True,
        related_name="orders",
    )

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


class CardAllocation(models.Model):
    """One physical card slot in an order, filled by seller preparation."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="allocations")
    position = models.PositiveIntegerField()
    card = models.OneToOneField(
        "cards.NFCCard", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="allocation",
    )
    representative = models.ForeignKey(
        "profiles.BusinessRepresentative", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="allocations",
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["order", "position"], name="unique_order_card_position")]
        ordering = ["position"]

    def __str__(self):
        return f"Order {self.order_id} card {self.position}"
