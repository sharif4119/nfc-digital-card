from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from products.models import Product


class ProductCatalogTests(TestCase):
    def setUp(self):
        self.personal = Product.objects.create(
            name="Personal One", card_category="PERSONAL",
            price=Decimal("650.00"), is_available=True,
        )
        self.business = Product.objects.create(
            name="Business One", card_category="BUSINESS",
            price=Decimal("1200.00"), is_available=True,
        )
        self.unavailable = Product.objects.create(
            name="Hidden Personal", card_category="PERSONAL",
            price=Decimal("700.00"), is_available=False,
        )

    def test_catalog_sections_use_category_querysets_without_duplicates(self):
        response = self.client.get(reverse("product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["personal_products"]), [self.personal])
        self.assertEqual(list(response.context["business_products"]), [self.business])
        self.assertContains(response, "Personal NFC Cards")
        self.assertContains(response, "Business NFC Cards")
        self.assertContains(response, "Personal One", count=1)
        self.assertContains(response, "Business One", count=1)
        self.assertNotContains(response, "Hidden Personal")
        self.assertNotContains(response, "shared business profile with one card")
        self.assertContains(response, reverse("home"))
        self.assertContains(response, "Back to Home")

    def test_empty_category_has_its_own_state(self):
        Product.objects.filter(card_category="BUSINESS").delete()
        response = self.client.get(reverse("product_list"))
        self.assertContains(response, "There are no Business NFC Cards available right now.")
        self.assertContains(response, "Personal One")

    def test_product_prices_and_order_actions_remain_category_specific(self):
        response = self.client.get(reverse("product_list"))
        self.assertContains(response, "৳650.00")
        self.assertContains(response, "৳1200.00")
        self.assertContains(response, reverse("product_detail", args=[self.personal.pk]))
        self.assertContains(response, reverse("create_order", args=[self.business.pk]))

    def test_product_detail_back_link_returns_to_cards(self):
        response = self.client.get(reverse("product_detail", args=[self.personal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("product_list"))
        self.assertContains(response, "Back to Cards")
