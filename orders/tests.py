from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cards.models import NFCCard
from products.models import Product

from .admin import OrderAdmin
from .models import CardAllocation, Order


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

        response = self.client.get(reverse("customer_order_detail", args=[1]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Order 1")
        self.assertNotContains(response, f"Order #{self.order.pk}")
        self.assertContains(
            response,
            "Payment and confirmation will be handled by the seller.",
        )
        self.assertNotContains(response, "Pay Now")
        self.assertContains(response, reverse("order_list"))
        self.assertContains(response, "Back to My Orders")

        legacy_response = self.client.get(reverse("order_detail", args=[self.order.pk]), follow=True)
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(legacy_response.request["PATH_INFO"], reverse("customer_order_detail", args=[1]))
        self.assertNotContains(legacy_response, f"/orders/{self.order.pk}/")

    def test_order_list_dashboard_and_details_use_account_local_order_numbers(self):
        later_order = Order.objects.create(
            user=self.user, product=self.product, quantity=1, price=self.product.price,
            customer_name="Second Customer", phone="01700000001", address="Second address", city="Dhaka",
        )
        self.client.force_login(self.user)

        history = self.client.get(reverse("order_list"))
        dashboard = self.client.get(reverse("dashboard"))
        detail = self.client.get(reverse("customer_order_detail", args=[1]))

        for response in (history, dashboard):
            self.assertContains(response, "My Order 1")
            self.assertContains(response, "My Order 2")
            self.assertNotContains(response, f"Order #{self.order.pk}")
            self.assertNotContains(response, f"Order #{later_order.pk}")
            self.assertNotContains(response, f"/orders/{self.order.pk}/")
            self.assertNotContains(response, f"/orders/{later_order.pk}/")
        self.assertContains(detail, "My Order 1")
        self.assertNotContains(detail, f"Order #{self.order.pk}")

        other_order = Order.objects.create(
            user=self.other_user, product=self.product, quantity=1, price=self.product.price,
            customer_name="Other Customer", phone="01700000002", address="Other address", city="Dhaka",
        )
        self.client.force_login(self.other_user)
        other_history = self.client.get(reverse("order_list"))
        self.assertContains(other_history, "My Order 1")
        self.assertNotContains(other_history, "My Order 2")
        self.assertNotContains(other_history, f"Order #{other_order.pk}")

    def test_order_details_number_every_allocation_from_card_one(self):
        CardAllocation.objects.create(order=self.order, position=1)
        multiple_order = Order.objects.create(
            user=self.user, product=self.product, quantity=2, price=self.product.price * 2,
            customer_name="Multiple Customer", phone="01700000003", address="Multi address", city="Dhaka",
        )
        CardAllocation.objects.bulk_create([
            CardAllocation(order=multiple_order, position=1),
            CardAllocation(order=multiple_order, position=2),
        ])
        self.client.force_login(self.user)

        single_detail = self.client.get(reverse("customer_order_detail", args=[1]))
        multiple_detail = self.client.get(reverse("customer_order_detail", args=[2]))

        self.assertContains(single_detail, "Card 1 · Representative pending")
        self.assertContains(multiple_detail, "Card 1 · Representative pending")
        self.assertContains(multiple_detail, "Card 2 · Representative pending")
        self.assertNotContains(single_detail, f"/orders/{self.order.pk}/")
        self.assertNotContains(multiple_detail, f"/orders/{multiple_order.pk}/")

    def test_create_order_has_back_link_to_product_details(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("create_order", args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("product_detail", args=[self.product.pk]))
        self.assertContains(response, "Back to Product Details")

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
                "customer_order_detail",
                args=[2],
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
            reverse("customer_order_detail", args=[2]),
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
