from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cards.models import NFCCard
from products.models import Product

from .admin import OrderAdmin
from .models import Order


class OrderFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-customer",
            password="test-password",
        )
        self.product = Product.objects.create(
            name="Standard NFC Card",
            price=Decimal("750.00"),
            is_available=True,
        )
        self.order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            price=self.product.price,
            customer_name="Test Customer",
            phone="01700000000",
            address="Test address",
            city="Dhaka",
        )

    def test_order_detail_page_renders(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "order_detail",
                args=[self.order.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order #")
        self.assertContains(
            response,
            "Payment and confirmation will be handled by the seller.",
        )
        self.assertNotContains(response, "Pay Now")

    def test_logged_out_user_cannot_order(self):
        response = self.client.get(
            reverse(
                "create_order",
                args=[self.product.pk],
            )
        )

        self.assertRedirects(
            response,
            (
                f"{reverse('login')}?next="
                f"{reverse('create_order', args=[self.product.pk])}"
            ),
        )

    def test_another_user_cannot_access_order(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse(
                "order_detail",
                args=[self.order.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_order_creation_always_stores_quantity_one(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "create_order",
                args=[self.product.pk],
            ),
            {
                "customer_name": "Test Customer",
                "phone": "01700000000",
                "address": "Test address",
                "city": "Dhaka",
                "quantity": 5,
            },
        )

        created_order = Order.objects.exclude(
            pk=self.order.pk
        ).get()

        self.assertRedirects(
            response,
            reverse(
                "order_detail",
                args=[created_order.pk],
            ),
        )
        self.assertEqual(created_order.quantity, 1)
        self.assertEqual(
            created_order.price,
            self.product.price,
        )

    def test_logged_in_user_can_submit_unpaid_pending_order(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "create_order",
                args=[self.product.pk],
            ),
            {
                "customer_name": "Demo Customer",
                "phone": "01711111111",
                "address": "Demo address",
                "city": "Dhaka",
            },
            follow=True,
        )

        created_order = Order.objects.exclude(
            pk=self.order.pk
        ).get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.request["PATH_INFO"],
            reverse("order_detail", args=[created_order.pk]),
        )
        self.assertEqual(created_order.payment_status, "UNPAID")
        self.assertEqual(created_order.order_status, "PENDING")
        self.assertContains(
            response,
            (
                "Order submitted successfully. Payment and confirmation "
                "will be handled by the seller."
            ),
        )
        self.assertNotContains(response, "Pay Now")
        self.assertNotContains(response, "Checkout")
        self.assertNotContains(response, "SSLCOMMERZ")

    def test_payment_routes_are_not_publicly_included(self):
        self.client.force_login(self.user)

        response = self.client.get(
            f"/payment/{self.order.pk}/"
        )

        self.assertEqual(response.status_code, 404)


class OrderAdminCardAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="card-owner",
            password="test-password",
        )
        self.product = Product.objects.create(
            name="Standard NFC Card",
            price=Decimal("750.00"),
        )
        self.order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            price=self.product.price,
            customer_name="Card Owner",
            phone="01700000000",
            address="Test address",
            city="Dhaka",
        )
        self.card = NFCCard.objects.create(
            card_uid="CARD-001",
        )
        self.order_admin = OrderAdmin(
            Order,
            admin.site,
        )
        self.request = RequestFactory().post(
            "/admin/orders/order/"
        )

    def test_assigning_card_marks_assigned_and_links_owner(self):
        self.order.assigned_card = self.card

        self.order_admin.save_model(
            self.request,
            self.order,
            form=None,
            change=True,
        )

        self.order.refresh_from_db()
        self.card.refresh_from_db()

        self.assertEqual(
            self.order.assigned_card,
            self.card,
        )
        self.assertEqual(
            self.order.order_status,
            "CARD_ASSIGNED",
        )
        self.assertEqual(self.card.owner, self.user)
        self.assertEqual(self.card.status, "ASSIGNED")
        self.assertIsNone(self.card.programmed_at)
        self.assertIsNone(self.card.programmed_by)
        self.assertIsNone(self.card.activated_at)
       

    def test_removing_card_resets_unpaid_order_to_pending(self):
        self.order.assigned_card = self.card
        self.order_admin.save_model(
            self.request,
            self.order,
            form=None,
            change=True,
        )

        self.order.assigned_card = None
        self.order_admin.save_model(
            self.request,
            self.order,
            form=None,
            change=True,
        )

        self.order.refresh_from_db()
        self.card.refresh_from_db()

        self.assertIsNone(self.order.assigned_card)
        self.assertEqual(
            self.order.order_status,
            "PENDING",
        )
        self.assertIsNone(self.card.owner)
        self.assertEqual(self.card.status, "UNASSIGNED")
        self.assertIsNone(self.card.activated_at)
