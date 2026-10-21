from django.db import models


class Product(models.Model):
    CARD_CATEGORIES = [("PERSONAL", "Personal card"), ("BUSINESS", "Business card")]
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )

    is_available = models.BooleanField(default=True)
    card_category = models.CharField(max_length=12, choices=CARD_CATEGORIES, default="PERSONAL")
    # Legacy metadata retained so existing product rows are not destructively
    # migrated. Card stock is now centrally fixed to CR80 in the print service.
    card_width_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    card_height_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
