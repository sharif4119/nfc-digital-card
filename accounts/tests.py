from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from cards.models import NFCCard
from orders.models import Order
from products.models import Product


class CustomerRegistrationTests(TestCase):
    password = "48271936"

    def registration_data(self, display_username, email, password=None):
        password = password or self.password
        return {
            "display_username": display_username,
            "email": email,
            "password1": password,
            "password2": password,
        }

    def test_customers_can_share_a_display_username(self):
        first_response = self.client.post(
            reverse("register"),
            self.registration_data("Alex", "alex-one@example.com"),
        )
        self.assertRedirects(first_response, reverse("dashboard"))
        self.client.logout()

        second_response = self.client.post(
            reverse("register"),
            self.registration_data("Alex", "alex-two@example.com"),
        )

        self.assertRedirects(second_response, reverse("dashboard"))
        customers = User.objects.filter(
            email__in=[
                "alex-one@example.com",
                "alex-two@example.com",
            ]
        ).order_by("email")
        self.assertEqual(customers.count(), 2)
        self.assertNotEqual(
            customers[0].username,
            customers[1].username,
        )
        self.assertTrue(customers[0].username.startswith("customer_"))
        self.assertTrue(customers[1].username.startswith("customer_"))
        self.assertEqual(customers[0].profile.display_username, "Alex")
        self.assertEqual(customers[1].profile.display_username, "Alex")

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.client.post(
            reverse("register"),
            self.registration_data("First", "Case@Example.com"),
        )
        self.client.logout()

        response = self.client.post(
            reverse("register"),
            self.registration_data("Second", "CASE@example.COM"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "An account with this email already exists.",
        )
        self.assertEqual(
            User.objects.filter(email__iexact="case@example.com").count(),
            1,
        )

    def test_database_enforces_case_insensitive_login_email(self):
        first = User.objects.create_user(username="first-profile")
        second = User.objects.create_user(username="second-profile")
        first.profile.login_email = "unique@example.com"
        first.profile.save(update_fields=["login_email"])
        second.profile.login_email = "UNIQUE@example.com"

        with self.assertRaises(IntegrityError), transaction.atomic():
            second.profile.save(update_fields=["login_email"])

    def test_integrity_error_is_shown_as_registration_error(self):
        with patch(
            "accounts.views.RegisterForm.save",
            side_effect=IntegrityError,
        ):
            response = self.client.post(
                reverse("register"),
                self.registration_data(
                    "Concurrent Customer",
                    "concurrent@example.com",
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "An account with this email already exists.",
        )
        self.assertFalse(
            User.objects.filter(email="concurrent@example.com").exists()
        )

    def test_exactly_eight_numeric_characters_are_accepted(self):
        response = self.client.post(
            reverse("register"),
            self.registration_data(
                "Eight Characters",
                "eight@example.com",
                password="48271936",
            ),
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(email="eight@example.com")
        self.assertTrue(user.check_password("48271936"))

    def test_nonempty_password_shorter_than_eight_characters_is_accepted(self):
        response = self.client.post(
            reverse("register"),
            self.registration_data(
                "Short Password",
                "short@example.com",
                password="5839172",
            ),
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.get(email="short@example.com").check_password("5839172"))

    def test_registration_accepts_common_numeric_alphabetic_and_mixed_passwords(self):
        cases = [
            ("common", "password"),
            ("numeric", "12345"),
            ("letters", "letters"),
            ("mixed", "A!2x"),
        ]
        for label, password in cases:
            with self.subTest(password=password):
                response = self.client.post(
                    reverse("register"),
                    self.registration_data(
                        label,
                        f"{label}@example.com",
                        password=password,
                    ),
                )
                self.assertRedirects(response, reverse("dashboard"))
                customer = User.objects.get(email=f"{label}@example.com")
                self.assertTrue(customer.check_password(password))
                self.client.logout()

    def test_registration_requires_nonempty_matching_passwords(self):
        empty_response = self.client.post(
            reverse("register"),
            {
                **self.registration_data("Empty Password", "empty@example.com"),
                "password1": "",
                "password2": "",
            },
        )
        self.assertEqual(empty_response.status_code, 200)
        self.assertContains(empty_response, "This field is required.")
        self.assertFalse(User.objects.filter(email="empty@example.com").exists())

        mismatch_data = self.registration_data("Mismatch", "mismatch@example.com")
        mismatch_data["password2"] = "different"
        mismatch_response = self.client.post(reverse("register"), mismatch_data)
        self.assertEqual(mismatch_response.status_code, 200)
        self.assertContains(mismatch_response, "The two password fields didn’t match")
        self.assertFalse(User.objects.filter(email="mismatch@example.com").exists())

    def test_registration_password_help_matches_relaxed_rules(self):
        response = self.client.get(reverse("register"))
        self.assertContains(response, "Choose any non-empty password")
        self.assertNotContains(response, "at least 8 characters")

    def test_dashboard_business_actions_are_inside_non_overlapping_content(self):
        from profiles.models import BusinessProfile

        user = User.objects.create_user(username="dashboard-customer", password="pass")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        html = response.content.decode()
        hero_end = html.index("</section>", html.index('class="dashboard-hero"'))
        content_start = html.index('class="dashboard-content"')
        button_start = html.index("Create Business Profile")
        self.assertGreater(button_start, content_start)
        self.assertGreater(button_start, hero_end)
        self.assertContains(response, 'class="dashboard-actions')

        BusinessProfile.objects.create(
            owner=user, name="Example Organization", profile_type="ORGANIZATION",
        )
        organization_dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(organization_dashboard, "Edit Organization Profile")
        self.assertContains(organization_dashboard, "Organization inquiries")

    def test_registration_and_login_have_accessible_password_toggles(self):
        register_response = self.client.get(reverse("register"))
        login_response = self.client.get(reverse("login"))

        self.assertContains(
            register_response,
            "data-password-toggle",
            count=2,
        )
        self.assertContains(
            register_response,
            'aria-controls="id_password1"',
        )
        self.assertContains(
            register_response,
            'aria-controls="id_password2"',
        )
        self.assertContains(
            login_response,
            "data-password-toggle",
            count=1,
        )
        self.assertContains(login_response, 'type="button"')
        self.assertContains(login_response, "Email or username")
        self.assertContains(register_response, reverse("home"))
        self.assertContains(register_response, "Back to Home")
        self.assertContains(login_response, reverse("home"))
        self.assertContains(login_response, "Back to Home")

    def test_new_customer_can_login_with_email_and_sees_display_name(self):
        self.client.post(
            reverse("register"),
            self.registration_data(
                "Visible Customer",
                "visible@example.com",
            ),
        )
        customer = User.objects.get(email="visible@example.com")
        internal_username = customer.username
        self.client.logout()

        response = self.client.post(
            reverse("login"),
            {
                "username": "VISIBLE@example.com",
                "password": self.password,
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, "Visible Customer")
        self.assertNotContains(dashboard, internal_username)


class AuthenticationCompatibilityTests(TestCase):
    def setUp(self):
        self.legacy_user = User.objects.create_user(
            username="legacy-customer",
            email="legacy@example.com",
            password="legacy-pass-123",
        )
        self.product = Product.objects.create(
            name="Legacy NFC Card",
            price=Decimal("750.00"),
        )
        self.order = Order.objects.create(
            user=self.legacy_user,
            product=self.product,
            quantity=1,
            price=self.product.price,
            customer_name="Legacy Customer",
            phone="01700000000",
            address="Test address",
            city="Dhaka",
        )
        self.card = NFCCard.objects.create(
            card_uid="LEGACY-ACCOUNT-CARD",
            owner=self.legacy_user,
            status="ACTIVE",
        )

    def test_existing_customer_username_login_and_relationships_are_preserved(self):
        user_id = self.legacy_user.id
        order_id = self.order.id
        card_id = self.card.id

        response = self.client.post(
            reverse("login"),
            {
                "username": "legacy-customer",
                "password": "legacy-pass-123",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.legacy_user.refresh_from_db()
        self.order.refresh_from_db()
        self.card.refresh_from_db()
        self.assertEqual(self.legacy_user.id, user_id)
        self.assertEqual(self.order.id, order_id)
        self.assertEqual(self.order.user_id, user_id)
        self.assertEqual(self.card.id, card_id)
        self.assertEqual(self.card.owner_id, user_id)

    def test_staff_username_login_and_seller_login_still_work(self):
        staff = User.objects.create_user(
            username="seller-staff",
            password="seller-pass-123",
            is_staff=True,
        )

        web_response = self.client.post(
            reverse("login"),
            {
                "username": staff.username,
                "password": "seller-pass-123",
            },
        )
        self.assertRedirects(web_response, reverse("dashboard"))
        self.client.logout()

        admin_response = self.client.post(
            reverse("admin:login"),
            {
                "username": staff.username,
                "password": "seller-pass-123",
                "next": reverse("admin:index"),
            },
        )
        self.assertRedirects(admin_response, reverse("admin:index"))
        self.client.logout()

        seller_response = self.client.post(
            reverse("seller_api_login"),
            {
                "username": staff.username,
                "password": "seller-pass-123",
            },
        )

        self.assertEqual(seller_response.status_code, 200)
        self.assertIn("token", seller_response.json())
