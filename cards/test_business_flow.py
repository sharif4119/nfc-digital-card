from decimal import Decimal
from unittest.mock import patch

import qrcode
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token

from cards.models import CardInquiry, CardVisit, NFCCard
from orders.models import CardAllocation, Order
from products.models import Product
from profiles.models import BusinessProfile, BusinessRepresentative
from seller_api.print_design import CR80_SIZE, build_card_print_images


@override_settings(PUBLIC_BASE_URL="https://nextap.pythonanywhere.com")
class BusinessCardFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("buyer", password="test-password")
        self.other = User.objects.create_user("other", password="test-password")
        self.staff = User.objects.create_user("seller", password="test-password", is_staff=True)
        self.business = BusinessProfile.objects.create(
            owner=self.owner, name="DIIT", description="Learning, together",
            phone="01700000000", email="hello@example.com",
        )
        self.personal = Product.objects.create(name="Personal", price=Decimal("600.00"))
        self.product = Product.objects.create(
            name="Business", card_category="BUSINESS", price=Decimal("1000.00"),
        )
        self.data = {"customer_name": "Buyer", "phone": "01700000000", "address": "Road 1", "city": "Dhaka"}

    def _order(self, product, kind="SINGLE", quantity=1):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("create_order", args=[product.id]), {
            **self.data, "business_order_type": kind, "quantity": quantity,
        })
        self.assertEqual(response.status_code, 302)
        return Order.objects.latest("id")

    def _prepare(self, order, allocation):
        token = Token.objects.get_or_create(user=self.staff)[0]
        self.client.force_login(self.staff)
        return self.client.post(reverse("seller_api_prepare_allocation", args=[order.id, allocation.id]), HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_personal_order_ignores_submitted_quantity(self):
        order = self._order(self.personal, quantity=5)
        self.assertEqual(order.quantity, 1)
        self.assertEqual(order.price, Decimal("600.00"))
        self.assertEqual(order.allocations.count(), 1)

    def test_business_single_and_multiple_orders_use_server_prices(self):
        single = self._order(self.product, "SINGLE", 1)
        self.assertEqual(single.price, Decimal("1000.00"))
        self.assertEqual(single.allocations.count(), 1)
        multiple = self._order(self.product, "MULTIPLE", 3)
        self.assertEqual(multiple.price, Decimal("3000.00"))
        self.assertEqual(multiple.allocations.count(), 3)
        self.assertEqual(multiple.business_profile, self.business)

    def test_business_card_pages_have_parent_navigation(self):
        order = self._order(self.product, "SINGLE", 1)
        allocation = order.allocations.first()
        cards_response = self.client.get(reverse("business_cards"))
        self.assertContains(cards_response, reverse("dashboard"))
        representative_response = self.client.get(reverse("representative_edit", args=[allocation.id]))
        self.assertContains(representative_response, reverse("business_cards"))
        self.assertContains(representative_response, "Back to Business Cards")

    def test_multiple_prepare_creates_unique_cards_and_keeps_legacy_field(self):
        order = self._order(self.product, "MULTIPLE", 2)
        allocations = list(order.allocations.all())
        first = self._prepare(order, allocations[0])
        second = self._prepare(order, allocations[1])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(NFCCard.objects.count(), 2)
        order.refresh_from_db()
        allocations[0].refresh_from_db()
        allocations[1].refresh_from_db()
        self.assertEqual(order.assigned_card, allocations[0].card)
        self.assertEqual(order.order_status, "CARD_ASSIGNED")
        self.assertNotEqual(allocations[0].card.public_token, allocations[1].card.public_token)
        self.assertNotEqual(allocations[0].card.card_uid, allocations[1].card.card_uid)
        self.assertEqual(allocations[1].card.owner, self.owner)
        self.assertEqual(allocations[1].card.status, "ASSIGNED")
        self.assertEqual(second.json()["allocations"][1]["card"]["public_url"], allocations[1].card.public_url)
        self._prepare(order, allocations[0])
        self.assertEqual(NFCCard.objects.count(), 2)

    def test_shared_business_and_distinct_representatives_and_individual_activation(self):
        self.business.show_owner_identity = True
        self.business.save()
        order = self._order(self.product, "MULTIPLE", 2)
        allocations = list(order.allocations.all())
        self.client.post(reverse("representative_edit", args=[allocations[0].id]), {"name": "Rahim", "designation": "Manager", "phone": "01711111111", "email": ""})
        self.client.post(reverse("representative_edit", args=[allocations[1].id]), {"name": "Karim", "designation": "Director", "phone": "", "email": ""})
        for allocation in allocations:
            self._prepare(order, allocation)
            allocation.refresh_from_db()
            self.assertEqual(allocation.card.business_profile, self.business)
        first_card, second_card = allocations[0].card, allocations[1].card
        for endpoint in ("seller_api_programmed", "seller_api_activate"):
            self.client.post(reverse(endpoint, args=[first_card.id]), HTTP_AUTHORIZATION=f"Token {Token.objects.get(user=self.staff).key}")
        first_card.refresh_from_db()
        second_card.refresh_from_db()
        self.assertEqual(first_card.status, "ACTIVE")
        self.assertEqual(second_card.status, "ASSIGNED")
        response = self.client.get(reverse("public_card", args=[first_card.public_token]))
        self.assertContains(response, "DIIT")
        self.assertContains(response, "Rahim")
        self.assertNotContains(response, "Karim")
        self.assertEqual(self.client.get(reverse("public_card", args=[second_card.public_token])).status_code, 404)
        for endpoint in ("seller_api_programmed", "seller_api_activate"):
            self.client.post(reverse(endpoint, args=[second_card.id]), HTTP_AUTHORIZATION=f"Token {Token.objects.get(user=self.staff).key}")
        self.assertContains(self.client.get(reverse("public_card", args=[second_card.public_token])), "Karim")
        self.business.description = "Updated shared identity"
        self.business.save()
        self.assertContains(self.client.get(reverse("public_card", args=[first_card.public_token])), "Updated shared identity")
        self.assertContains(self.client.get(reverse("public_card", args=[second_card.public_token])), "Updated shared identity")

    def test_other_customer_cannot_edit_business_or_representative(self):
        order = self._order(self.product)
        allocation = order.allocations.get()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("representative_edit", args=[allocation.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("business_cards")).status_code, 302)
        response = self.client.post(reverse("business_edit"), {"name": "Other Business", "offerings-TOTAL_FORMS": "0", "offerings-INITIAL_FORMS": "0"})
        self.assertNotEqual(response.status_code, 500)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "DIIT")

    def test_offline_vcard_qr_and_online_qr_remain_distinct(self):
        order = self._order(self.product)
        allocation = order.allocations.get()
        self._prepare(order, allocation)
        allocation.refresh_from_db()
        card = allocation.card
        card.status = "ACTIVE"
        card.save(update_fields=["status"])
        with patch("cards.views.qrcode.make") as make:
            make.return_value.save = lambda buffer, format: buffer.write(b"PNG")
            response = self.client.get(reverse("offline_contact_qr", args=[card.public_token]))
            self.assertEqual(response.status_code, 200)
            payload = make.call_args.args[0]
            self.assertIn("BEGIN:VCARD", payload)
            self.assertIn(card.public_url, payload)
            self.assertIn("ORG:DIIT", payload)
            self.client.get(reverse("card_qr", args=[card.public_token]))
            self.assertEqual(make.call_args.args[0], card.public_url)

    def test_visits_inquiries_and_owner_visibility(self):
        order = self._order(self.product)
        allocation = order.allocations.get()
        self._prepare(order, allocation)
        allocation.refresh_from_db()
        card = allocation.card
        card.status = "ACTIVE"
        card.save(update_fields=["status"])
        url = reverse("public_card", args=[card.public_token])
        self.client.get(url)
        self.client.get(url)
        self.assertEqual(CardVisit.objects.filter(card=card).count(), 2)
        self.assertEqual(CardVisit.objects.filter(card=card).values("visitor_hash").distinct().count(), 1)
        self.client.get(reverse("offline_contact_qr", args=[card.public_token]))
        self.assertEqual(CardVisit.objects.filter(card=card).count(), 2)
        inquiry = {"name": "Visitor", "email": "visitor@example.com", "interest": "Courses", "message": "Please call", "consent": "on"}
        self.assertEqual(self.client.post(url, inquiry).status_code, 302)
        self.assertEqual(CardInquiry.objects.filter(card=card).count(), 1)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("business_cards")), "Visitor")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("dashboard")), "visitor@example.com")

    def test_inquiry_needs_consent_and_rate_limit(self):
        order = self._order(self.product)
        allocation = order.allocations.get()
        self._prepare(order, allocation)
        allocation.refresh_from_db()
        card = allocation.card
        card.status = "ACTIVE"
        card.save(update_fields=["status"])
        url = reverse("public_card", args=[card.public_token])
        data = {"name": "Visitor", "email": "visitor@example.com", "interest": "Courses"}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(CardInquiry.objects.count(), 0)
        for _ in range(3):
            self.assertEqual(self.client.post(url, {**data, "consent": "on"}).status_code, 302)
        self.assertEqual(self.client.post(url, {**data, "consent": "on"}).status_code, 200)
        self.assertEqual(CardInquiry.objects.count(), 3)

    def test_business_pdf_contains_offline_contact_qr_and_stock_size(self):
        order = self._order(self.product)
        allocation = order.allocations.get()
        self._prepare(order, allocation)
        allocation.refresh_from_db()
        card = allocation.card
        with patch("seller_api.print_design.qrcode.make", wraps=__import__("qrcode").make) as make_qr:
            response = self.client.get(reverse("seller_api_card_print_pdf", args=[card.id]), HTTP_AUTHORIZATION=f"Token {Token.objects.get(user=self.staff).key}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("BEGIN:VCARD", make_qr.call_args.args[0])
        self.assertIn(card.public_url, make_qr.call_args.args[0])
        self.assertEqual(build_card_print_images(card)[0].size, CR80_SIZE)

    def test_personal_pdf_contains_saved_personal_contact_and_profile_url(self):
        order = self._order(self.personal)
        allocation = order.allocations.get()
        self._prepare(order, allocation)
        allocation.refresh_from_db()
        card = allocation.card
        with patch("seller_api.print_design.qrcode.make", wraps=__import__("qrcode").make) as make_qr:
            response = self.client.get(
                reverse("seller_api_card_print_pdf", args=[card.id]),
                HTTP_AUTHORIZATION=f"Token {Token.objects.get(user=self.staff).key}",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("BEGIN:VCARD", make_qr.call_args.args[0])
        self.assertIn("FN:buyer", make_qr.call_args.args[0])
        self.assertIn(card.public_url, make_qr.call_args.args[0])
        self.assertEqual(build_card_print_images(card)[0].size, CR80_SIZE)

    def test_business_print_qr_matches_each_representative(self):
        self.business.show_owner_identity = True
        self.business.save()
        order = self._order(self.product, "MULTIPLE", 2)
        allocations = list(order.allocations.all())
        expected = ["Rahim", "Karim"]
        for allocation, name in zip(allocations, expected):
            representative = BusinessRepresentative.objects.create(
                business=self.business, name=name, designation="Representative",
            )
            allocation.representative = representative
            allocation.save(update_fields=["representative"])
            self._prepare(order, allocation)
            allocation.refresh_from_db()
        for allocation, name in zip(allocations, expected):
            with self.subTest(representative=name):
                with patch("seller_api.print_design.qrcode.make", wraps=__import__("qrcode").make) as make_qr:
                    response = self.client.get(
                        reverse("seller_api_card_print_pdf", args=[allocation.card_id]),
                        HTTP_AUTHORIZATION=f"Token {Token.objects.get(user=self.staff).key}",
                    )
                self.assertEqual(response.status_code, 200)
                self.assertIn(f"FN:{name}", make_qr.call_args.args[0])
                self.assertIn(allocation.card.public_url, make_qr.call_args.args[0])

    def test_vcard_escapes_business_text_and_includes_public_url(self):
        self.business.name = "Cake, Co; Studio"
        self.business.save()
        order = self._order(self.product)
        allocation = order.allocations.get()
        self._prepare(order, allocation)
        allocation.refresh_from_db()
        card = allocation.card
        card.status = "ACTIVE"
        card.save(update_fields=["status"])
        response = self.client.get(reverse("download_vcard", args=[card.public_token]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("ORG:Cake\\, Co\\; Studio", response.content.decode())
        self.assertIn(card.public_url, response.content.decode())

    def test_business_order_requires_owned_profile_and_valid_quantity(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("create_order", args=[self.product.id]), {**self.data, "business_order_type": "MULTIPLE", "quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.client.force_login(self.owner)
        response = self.client.post(reverse("create_order", args=[self.product.id]), {**self.data, "business_order_type": "SINGLE", "quantity": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_new_business_profile_and_offering_can_be_saved_by_owner(self):
        self.client.force_login(self.other)
        data = {
            "name": "Cake Studio", "description": "Custom cakes", "phone": "",
            "email": "", "website": "", "address": "", "facebook": "",
            "instagram": "", "linkedin": "", "whatsapp": "",
            "offerings-TOTAL_FORMS": "1", "offerings-INITIAL_FORMS": "0",
            "offerings-MIN_NUM_FORMS": "0", "offerings-MAX_NUM_FORMS": "6",
            "offerings-0-name": "Chocolate cake", "offerings-0-description": "Freshly baked",
            "offerings-0-price": "500.00", "offerings-0-position": "1",
        }
        response = self.client.post(reverse("business_edit"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BusinessProfile.objects.get(owner=self.other).offerings.count(), 1)
        self.assertEqual(self.business.name, "DIIT")

    def test_new_prepare_endpoint_is_staff_only(self):
        order = self._order(self.product)
        allocation = order.allocations.get()
        url = reverse("seller_api_prepare_allocation", args=[order.id, allocation.id])
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 401)
        token = Token.objects.create(user=self.owner)
        self.assertEqual(self.client.post(url, HTTP_AUTHORIZATION=f"Token {token.key}").status_code, 403)
        self.assertEqual(NFCCard.objects.count(), 0)

    def test_products_need_no_dimensions_and_prints_share_cr80_but_keep_distinct_art(self):
        # Product validation no longer requires product-specific dimensions.
        new_product = Product(name="Another personal", price=Decimal("750.00"))
        new_product.full_clean()
        self.assertIsNone(new_product.card_width_mm)
        self.assertIsNone(new_product.card_height_mm)

        personal_order = self._order(self.personal)
        business_order = self._order(self.product)
        self.assertEqual(personal_order.price, Decimal("600.00"))
        self.assertEqual(business_order.price, Decimal("1000.00"))

        printed = []
        for order in (personal_order, business_order):
            allocation = order.allocations.get()
            self._prepare(order, allocation)
            allocation.refresh_from_db()
            front, back = build_card_print_images(allocation.card)
            self.assertEqual(front.size, CR80_SIZE)
            self.assertEqual(back.size, CR80_SIZE)
            printed.append((front, back))

        self.assertNotEqual(printed[0][0].tobytes(), printed[1][0].tobytes())
        # Both backs retain a working offline vCard QR, personalized per card.
        for order in (personal_order, business_order):
            card = order.allocations.get().card
            with patch("seller_api.print_design.qrcode.make", wraps=__import__("qrcode").make) as make_qr:
                build_card_print_images(card)
            self.assertIn("BEGIN:VCARD", make_qr.call_args.args[0])
            self.assertIn(card.public_url, make_qr.call_args.args[0])

    def test_product_admin_hides_legacy_dimension_fields(self):
        from django.contrib import admin
        from products.admin import ProductAdmin

        model_admin = ProductAdmin(Product, admin.site)
        form = model_admin.get_form(None)
        self.assertNotIn("card_width_mm", form.base_fields)
        self.assertNotIn("card_height_mm", form.base_fields)

    def test_historical_order_reprints_offline_vcard_qr_regardless_of_order_flag(self):
        order = Order.objects.create(
            user=self.owner, product=self.personal, quantity=1, price=self.personal.price,
            customer_name="Buyer", phone="01700000000", address="Road 1", city="Dhaka",
        )
        card = NFCCard.objects.create(card_uid="LEGACY-01", owner=self.owner, status="ASSIGNED")
        CardAllocation.objects.create(order=order, position=1, card=card)
        with patch("seller_api.print_design.qrcode.make", wraps=__import__("qrcode").make) as make_qr:
            build_card_print_images(card)
        payload = make_qr.call_args.args[0]
        self.assertIn("BEGIN:VCARD", payload)
        self.assertIn(card.public_url, payload)
        self.assertEqual(make_qr.call_args.kwargs["error_correction"], __import__("qrcode").constants.ERROR_CORRECT_M)

    def test_print_snapshot_uses_allocation_representative_for_legacy_order(self):
        self.business.show_owner_identity = True
        self.business.save()
        order = self._order(self.product, "SINGLE", 1)
        order.business_order_type = "MULTIPLE"
        order.save(update_fields=["business_order_type"])
        order.offline_contact_print = False
        order.save(update_fields=["offline_contact_print"])
        allocation = order.allocations.get()
        rep = BusinessRepresentative.objects.create(
            business=self.business, name="Print Representative", phone="01777777777", phone_public=True,
        )
        allocation.representative = rep
        allocation.save(update_fields=["representative"])
        self._prepare(order, allocation)
        allocation.refresh_from_db()
        card = allocation.card
        # The legacy order flag remains false: allocation identity still drives this reprint.
        order.refresh_from_db()
        self.assertFalse(order.offline_contact_print)

        with patch("seller_api.print_design.qrcode.make", wraps=__import__("qrcode").make) as make_qr:
            build_card_print_images(card)

        payload = make_qr.call_args.args[0]
        self.assertIn("FN:Print Representative", payload)
        self.assertIn("01777777777", payload)
        self.assertIn(card.public_url, payload)

    def test_offline_qr_module_size_is_suitable_for_cr80_prints(self):
        self.owner.profile.full_name = "Representative Person"
        self.owner.profile.phone = "+8801700111222"
        self.owner.profile.email = "person@example.test"
        self.owner.profile.bio = "Designer and owner " * 10
        self.owner.profile.save()
        cards = []
        personal_order = self._order(self.personal)
        personal_allocation = personal_order.allocations.get()
        self._prepare(personal_order, personal_allocation)
        personal_allocation.refresh_from_db()
        cards.append(personal_allocation.card)

        card_scenarios = (
            ("SMALL_BUSINESS", "COMPANY"),
            ("ORGANIZATION", "COMPANY"),
            ("ORGANIZATION", "EDUCATIONAL_INSTITUTE"),
        )
        for profile_type, organization_category in card_scenarios:
            self.business.profile_type = profile_type
            self.business.organization_category = organization_category
            self.business.phone = "+88025551234"
            self.business.email = "office@example.test"
            self.business.address = "Official Road, Dhaka"
            self.business.save()
            order = self._order(self.product, "SINGLE", 1)
            allocation = order.allocations.get()
            if profile_type == "ORGANIZATION":
                order.business_order_type = "MULTIPLE"
                order.save(update_fields=["business_order_type"])
                representative = BusinessRepresentative.objects.create(
                    business=self.business,
                    name=f"{organization_category} Representative",
                    designation="Director",
                    phone="+8801700111222",
                    email="representative@example.test",
                    phone_public=True,
                    email_public=True,
                )
                allocation.representative = representative
                allocation.save(update_fields=["representative"])
            self._prepare(order, allocation)
            allocation.refresh_from_db()
            cards.append(allocation.card)

        for card in cards:
            with self.subTest(card=card.card_uid):
                with patch("seller_api.print_design.qrcode.make", wraps=qrcode.make) as make_qr:
                    front, back = build_card_print_images(card)
                payload = make_qr.call_args.args[0]
                qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
                qr.add_data(payload)
                qr.make(fit=True)
                qr_width_mm = 430 / 300 * 25.4
                module_width_mm = qr_width_mm / (qr.modules_count + 8)
                self.assertGreaterEqual(module_width_mm, 0.35)
                self.assertEqual(front.size, CR80_SIZE)
                self.assertEqual(back.size, CR80_SIZE)
                self.assertIn(card.public_url, payload)

    def test_business_dashboard_keeps_card_statistics_separate(self):
        order = self._order(self.product, "MULTIPLE", 2)
        allocations = list(order.allocations.all())
        cards = []
        for allocation in allocations:
            self._prepare(order, allocation)
            allocation.refresh_from_db()
            allocation.card.status = "ACTIVE"
            allocation.card.save(update_fields=["status"])
            cards.append(allocation.card)
        self.client.get(reverse("public_card", args=[cards[0].public_token]))
        self.client.get(reverse("public_card", args=[cards[0].public_token]))
        self.client.get(reverse("public_card", args=[cards[1].public_token]))
        self.client.post(reverse("public_card", args=[cards[0].public_token]), {
            "name": "Visitor", "email": "visitor@example.com", "interest": "Courses", "consent": "on",
        })
        self.client.force_login(self.owner)
        response = self.client.get(reverse("business_cards"))
        rows = {row["card"].id: row for row in response.context["card_rows"]}
        self.assertEqual(rows[cards[0].id]["visits"], 2)
        self.assertEqual(rows[cards[1].id]["visits"], 1)
        self.assertEqual(rows[cards[0].id]["inquiries"], 1)
        self.assertEqual(rows[cards[1].id]["inquiries"], 0)
