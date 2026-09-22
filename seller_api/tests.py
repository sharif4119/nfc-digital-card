from decimal import Decimal
from unittest.mock import patch

import qrcode
from django.contrib.auth.models import User
from django.test import Client
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from cards.models import NFCCard
from orders.models import Order
from products.models import Product

from .print_design import CR80_SIZE, build_card_print_images


class PrepareCardAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="seller",
            password="test-pass-123",
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username="customer",
            password="test-pass-123",
        )
        self.product = Product.objects.create(
            name="NexTap Card",
            description="Test NFC card",
            price=Decimal("1200.00"),
            is_available=True,
        )
        self.order = self.create_order(self.customer)
        self.prepare_url = reverse(
            "seller_api_prepare_card",
            kwargs={"order_id": self.order.id},
        )

    def create_order(self, user):
        return Order.objects.create(
            user=user,
            product=self.product,
            quantity=1,
            price=self.product.price,
            customer_name=user.username,
            phone="01700000000",
            address="Test address",
            city="Dhaka",
        )

    def authenticate_staff(self):
        self.client.force_authenticate(user=self.staff)

    def test_prepare_card_requires_authentication(self):
        response = self.client.post(self.prepare_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_prepare_card_requires_staff_user(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(self.prepare_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_prepare_and_link_card(self):
        self.authenticate_staff()

        self.assertEqual(self.order.payment_status, "UNPAID")

        response = self.client.post(self.prepare_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        card = self.order.assigned_card
        self.assertIsNotNone(card)
        self.assertEqual(card.card_uid, "NXT-000001")
        self.assertEqual(card.owner, self.customer)
        self.assertEqual(card.status, "ASSIGNED")
        self.assertIsNone(card.programmed_at)
        self.assertIsNone(card.programmed_by)
        self.assertIsNone(card.activated_at)
        self.assertEqual(self.order.order_status, "CARD_ASSIGNED")

        card_data = response.data["assigned_card"]
        self.assertEqual(card_data["owner"], self.customer.id)
        self.assertEqual(card_data["owner_username"], self.customer.username)
        self.assertEqual(
            card_data["public_url"],
            card.public_url,
        )

    def test_generated_card_uids_are_unique(self):
        self.authenticate_staff()
        first_response = self.client.post(self.prepare_url)
        second_customer = User.objects.create_user(
            username="customer-two",
            password="test-pass-123",
        )
        second_order = self.create_order(second_customer)

        second_response = self.client.post(
            reverse(
                "seller_api_prepare_card",
                kwargs={"order_id": second_order.id},
            )
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            first_response.data["assigned_card"]["card_uid"],
            "NXT-000001",
        )
        self.assertEqual(
            second_response.data["assigned_card"]["card_uid"],
            "NXT-000002",
        )
        self.assertEqual(
            NFCCard.objects.values("card_uid").distinct().count(),
            2,
        )

    def test_generated_uid_skips_an_existing_manual_collision(self):
        NFCCard.objects.create(
            card_uid="NXT-000002",
            status="UNASSIGNED",
        )
        self.authenticate_staff()

        response = self.client.post(self.prepare_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["assigned_card"]["card_uid"],
            "NXT-000003",
        )
        self.assertTrue(
            NFCCard.objects.filter(card_uid="NXT-000002").exists()
        )

    def test_manual_uid_is_preserved_and_does_not_advance_sequence(self):
        manual_card = NFCCard.objects.create(
            card_uid="LEGACY-CARD-42",
            status="UNASSIGNED",
        )
        self.authenticate_staff()

        response = self.client.post(self.prepare_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["assigned_card"]["card_uid"],
            "NXT-000001",
        )
        manual_card.refresh_from_db()
        self.assertEqual(manual_card.card_uid, "LEGACY-CARD-42")

    def test_second_prepare_call_returns_same_card(self):
        self.authenticate_staff()
        first_response = self.client.post(self.prepare_url)
        card_count = NFCCard.objects.count()

        second_response = self.client.post(self.prepare_url)

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(NFCCard.objects.count(), card_count)
        self.assertEqual(
            second_response.data["assigned_card"]["id"],
            first_response.data["assigned_card"]["id"],
        )

    def test_conflicting_non_inactive_card_is_rejected(self):
        NFCCard.objects.create(
            card_uid="MANUAL-001",
            owner=self.customer,
            status="PROGRAMMED",
        )
        self.authenticate_staff()

        response = self.client.post(self.prepare_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non-inactive", response.data["detail"])
        self.assertEqual(NFCCard.objects.count(), 1)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.assigned_card)

    def test_assigned_and_programmed_cards_stay_private_until_active(self):
        self.authenticate_staff()
        response = self.client.post(self.prepare_url)
        card = NFCCard.objects.get(id=response.data["assigned_card"]["id"])
        public_url = reverse("public_card", args=[card.public_token])
        public_client = Client()

        self.assertEqual(public_client.get(public_url).status_code, 404)

        card.status = "PROGRAMMED"
        card.save(update_fields=["status"])
        self.assertEqual(public_client.get(public_url).status_code, 404)

        card.status = "ACTIVE"
        card.save(update_fields=["status"])
        self.assertEqual(public_client.get(public_url).status_code, 200)


@override_settings(
    PUBLIC_BASE_URL="https://nextap.pythonanywhere.com"
)
class CardPrintPDFAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="print-seller",
            password="test-pass-123",
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username="print-customer",
            password="test-pass-123",
        )
        self.card = NFCCard.objects.create(
            card_uid="NXT-PRINT-001",
            owner=self.customer,
            status="ASSIGNED",
        )
        self.product = Product.objects.create(
            name="Printable NexTap Card",
            price=Decimal("1200.00"),
            is_available=True,
        )
        self.order = Order.objects.create(
            user=self.customer,
            product=self.product,
            assigned_card=self.card,
            quantity=1,
            price=self.product.price,
            customer_name="Print Customer",
            phone="01700000000",
            address="Test address",
            city="Dhaka",
            order_status="CARD_ASSIGNED",
        )
        self.print_url = reverse(
            "seller_api_card_print_pdf",
            kwargs={"card_id": self.card.id},
        )
        self.card_detail_url = reverse(
            "seller_api_card_detail",
            kwargs={"card_id": self.card.id},
        )
        self.order_detail_url = reverse(
            "seller_api_order_detail",
            kwargs={"order_id": self.order.id},
        )

    def test_print_pdf_requires_authentication(self):
        response = self.client.get(self.print_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_print_pdf_requires_staff_user(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(self.print_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_receives_downloadable_front_back_pdf(self):
        token = Token.objects.create(user=self.staff)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}"
        )

        response = self.client.get(self.print_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            (
                'attachment; filename="NexTap-NXT-PRINT-001-'
                'front-back.pdf"'
            ),
        )
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertEqual(
            response.content.count(
                b"/MediaBox [ 0 0 242.64 153.12 ]"
            ),
            2,
        )

    def test_card_detail_exposes_canonical_print_pdf_url(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(self.card_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["print_pdf_url"],
            (
                "https://nextap.pythonanywhere.com"
                f"/api/seller/cards/{self.card.id}/print/"
            ),
        )

    def test_order_detail_contains_nested_print_pdf_url(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(self.order_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["assigned_card"]["print_pdf_url"],
            (
                "https://nextap.pythonanywhere.com"
                f"/api/seller/cards/{self.card.id}/print/"
            ),
        )

    def test_print_pdf_url_is_available_for_each_supported_status(self):
        self.client.force_authenticate(user=self.staff)

        for card_status in ("ASSIGNED", "PROGRAMMED", "ACTIVE"):
            with self.subTest(card_status=card_status):
                self.card.status = card_status
                self.card.save(update_fields=["status"])

                response = self.client.get(self.card_detail_url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn("print_pdf_url", response.data)

    def test_print_pdf_url_is_omitted_for_unsupported_statuses(self):
        self.client.force_authenticate(user=self.staff)

        for card_status in ("UNASSIGNED", "INACTIVE"):
            with self.subTest(card_status=card_status):
                self.card.status = card_status
                self.card.save(update_fields=["status"])

                response = self.client.get(self.card_detail_url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertNotIn("print_pdf_url", response.data)

    def test_print_design_uses_cr80_dimensions_at_300_dpi(self):
        front, back = build_card_print_images(self.card.public_url)

        self.assertEqual(CR80_SIZE, (1011, 638))
        self.assertEqual(front.size, CR80_SIZE)
        self.assertEqual(back.size, CR80_SIZE)

    def test_qr_uses_exact_canonical_card_public_url(self):
        self.client.force_authenticate(user=self.staff)

        with patch(
            "seller_api.print_design.qrcode.make",
            wraps=qrcode.make,
        ) as make_qr:
            response = self.client.get(self.print_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.card.public_url,
            (
                "https://nextap.pythonanywhere.com"
                f"/c/{self.card.public_token}/"
            ),
        )
        make_qr.assert_called_once_with(self.card.public_url)

    def test_printing_supports_lifecycle_status_without_mutation(self):
        self.client.force_authenticate(user=self.staff)

        for card_status in ("ASSIGNED", "PROGRAMMED", "ACTIVE"):
            with self.subTest(card_status=card_status):
                self.card.status = card_status
                self.card.save(update_fields=["status"])

                response = self.client.get(self.print_url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.card.refresh_from_db()
                self.assertEqual(self.card.status, card_status)
