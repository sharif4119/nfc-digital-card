from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cards.models import NFCCard
from orders.models import Order
from products.models import Product


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.test", password="test-password-123"
        )
        self.customer = User.objects.create_user(
            username="customer", email="customer@example.test", password="test-password-123"
        )
        self.product = Product.objects.create(name="Test card", price=Decimal("500.00"))

    def make_order(self, *, payment_status, quantity, order_status="PENDING"):
        return Order.objects.create(
            user=self.customer,
            product=self.product,
            quantity=quantity,
            price=Decimal("500.00") * quantity,
            customer_name="Test Customer",
            phone="01700000000",
            address="Test address",
            city="Dhaka",
            payment_status=payment_status,
            order_status=order_status,
        )

    def test_dashboard_requires_admin_access(self):
        url = reverse("admin:index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_staff_admin_can_access_dashboard_and_summary_counts_paid_sales_only(self):
        self.make_order(payment_status="PAID", quantity=2, order_status="PROCESSING")
        self.make_order(payment_status="UNPAID", quantity=3)
        NFCCard.objects.create(card_uid="ADMIN-UNASSIGNED", status="UNASSIGNED")
        NFCCard.objects.create(card_uid="ADMIN-ACTIVE", status="ACTIVE")

        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        stats = response.context["nxtap_admin_stats"]
        self.assertEqual(stats["total_orders"], 2)
        self.assertEqual(stats["cards_sold"], 2)
        self.assertEqual(stats["paid_revenue"], Decimal("1000.00"))
        self.assertEqual(stats["pending_orders"], 2)
        self.assertEqual(stats["unassigned_cards"], 1)
        self.assertEqual(stats["active_cards"], 1)
        self.assertContains(response, "Recent orders")
        self.assertContains(response, "Recently created cards")
        self.assertContains(response, "Available card products")
        self.assertContains(response, "Test card")
        self.assertContains(response, reverse("admin:products_product_add"))
        self.assertNotContains(response, '<section class="nxtap-admin-app-list">')


class CardAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="card-admin", email="card-admin@example.test", password="test-password-123"
        )

    def test_admin_card_creation_generates_identifiers_and_starts_unassigned(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("admin:cards_nfccard_add"), {})

        self.assertEqual(response.status_code, 302)
        card = NFCCard.objects.get()
        self.assertRegex(card.card_uid, r"^NXT-\d{6}$")
        self.assertTrue(card.public_token)
        self.assertEqual(card.status, "UNASSIGNED")
        self.assertIsNone(card.owner_id)

    def test_generated_identifiers_are_not_editable_and_state_is_read_only(self):
        card = NFCCard.objects.create(card_uid="MANUAL-ADMIN-1", status="ASSIGNED")
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:cards_nfccard_change", args=[card.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MANUAL-ADMIN-1")
        self.assertNotContains(response, 'name="card_uid"')
        self.assertNotContains(response, 'name="public_token"')
        self.assertNotContains(response, 'name="status"')


class UserAdminAccessTests(TestCase):
    def test_non_staff_cannot_open_user_management(self):
        user = User.objects.create_user(username="ordinary", password="test-password-123")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_user_admin_hides_password_hash_and_blocks_last_superuser_delete(self):
        admin_user = User.objects.create_superuser(
            username="only-admin", email="only-admin@example.test", password="test-password-123"
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse("admin:auth_user_change", args=[admin_user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, admin_user.password)
        model_admin = site._registry[User]
        request = RequestFactory().get("/admin/")
        request.user = admin_user
        self.assertFalse(model_admin.has_delete_permission(request, admin_user))
