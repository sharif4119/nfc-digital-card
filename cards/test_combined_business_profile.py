from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cards.contact import build_vcard
from cards.models import NFCCard
from orders.models import CardAllocation, Order
from products.models import Product
from profiles.models import BusinessProfile, BusinessRepresentative, Profile


class CombinedBusinessProfileTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("combined-owner", password="test-password")
        self.profile, _ = Profile.objects.get_or_create(user=self.owner)
        self.profile.full_name = "Private Owner Name"
        self.profile.job_title = "Founder"
        self.profile.phone = "+8801700111222"
        self.profile.email = "private@example.com"
        self.profile.save()
        self.business = BusinessProfile.objects.create(owner=self.owner, name="NexTap Kitchen")
        self.product = Product.objects.create(name="Business card", price=Decimal("900.00"), card_category="BUSINESS")

    def _card(self, position=1, kind="SINGLE", rep=None, status="ACTIVE"):
        order = Order.objects.create(
            user=self.owner, product=self.product, quantity=1, price=Decimal("900.00"),
            customer_name="Account Purchaser", phone="01700000000", address="Dhaka",
            city="Dhaka", business_order_type=kind, business_profile=self.business,
        )
        card = NFCCard.objects.create(
            card_uid=f"COMBINED-{kind}-{position}", owner=self.owner,
            business_profile=self.business, representative=rep, status=status,
        )
        order.assigned_card = card
        order.save(update_fields=["assigned_card"])
        allocation = CardAllocation.objects.create(
            order=order, position=position, card=card, representative=rep,
        )
        return order, allocation, card

    def test_existing_business_profiles_default_to_small_business(self):
        self.assertEqual(self.business.profile_type, "SMALL_BUSINESS")
        self.assertEqual(self.business.organization_category, "COMPANY")

    def test_business_editor_saves_organization_subtype_and_previews_it(self):
        self.client.force_login(self.owner)
        post = {
            "profile_type": "ORGANIZATION", "organization_category": "EDUCATIONAL_INSTITUTE",
            "name": "Learning Centre", "description": "Programs and learning", "website": "example.edu",
            "offerings-TOTAL_FORMS": "6", "offerings-INITIAL_FORMS": "0",
            "offerings-MIN_NUM_FORMS": "0", "offerings-MAX_NUM_FORMS": "6",
            "offerings-0-name": "Computing", "offerings-0-position": "1", "action": "preview",
        }
        response = self.client.post(reverse("business_edit"), post)
        self.assertRedirects(response, reverse("business_profile_preview"))
        self.business.refresh_from_db()
        self.assertEqual(self.business.profile_type, "ORGANIZATION")
        self.assertEqual(self.business.organization_category, "EDUCATIONAL_INSTITUTE")
        preview = self.client.get(response.url)
        self.assertContains(preview, "Academic Programs")
        self.assertContains(preview, "Representative details will appear after a person is assigned to this card.")
        self.assertContains(preview, "Computing")

    def test_organization_company_uses_products_and_services_label(self):
        self.business.profile_type = "ORGANIZATION"
        self.business.organization_category = "COMPANY"
        self.business.save()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("business_profile_preview"))
        self.assertContains(response, "Products &amp; Services")
        self.assertNotContains(response, "Academic Programs")

    def test_small_business_single_uses_owner_identity_only_after_opt_in(self):
        self.business.show_owner_identity = True
        self.business.share_owner_phone = True
        self.business.save()
        _, _, card = self._card()
        response = self.client.get(reverse("public_card", args=[card.public_token]))
        self.assertContains(response, "Private Owner Name")
        self.assertContains(response, "+8801700111222")
        self.assertNotContains(response, "private@example.com")
        self.assertNotContains(response, "Account Purchaser")

    def test_business_multiple_cards_use_only_their_own_representatives(self):
        first_rep = BusinessRepresentative.objects.create(business=self.business, name="Representative One")
        second_rep = BusinessRepresentative.objects.create(business=self.business, name="Representative Two")
        _, _, first = self._card(1, "MULTIPLE", first_rep)
        _, _, second = self._card(2, "MULTIPLE", second_rep)
        first_page = self.client.get(reverse("public_card", args=[first.public_token]))
        second_page = self.client.get(reverse("public_card", args=[second.public_token]))
        self.assertContains(first_page, "Representative One")
        self.assertNotContains(first_page, "Representative Two")
        self.assertNotContains(first_page, "Private Owner Name")
        self.assertContains(second_page, "Representative Two")
        self.assertNotContains(second_page, "Representative One")

    def test_organization_identity_is_representative_first_and_uses_academic_heading(self):
        self.business.profile_type = "ORGANIZATION"
        self.business.organization_category = "EDUCATIONAL_INSTITUTE"
        self.business.save()
        rep = BusinessRepresentative.objects.create(
            business=self.business, name="Principal Person", designation="Principal",
            email="principal@example.edu", email_public=True,
        )
        _, _, card = self._card(rep=rep)
        response = self.client.get(reverse("public_card", args=[card.public_token]))
        body = response.content.decode()
        self.assertLess(body.index("Principal Person"), body.index('<h2 id="nxt-business-name">'))
        self.assertContains(response, "Academic Programs")
        self.assertContains(response, "principal@example.edu")
        self.assertNotContains(response, "Private Owner Name")

    def test_private_preview_selects_only_owner_allocations(self):
        rep = BusinessRepresentative.objects.create(business=self.business, name="Selected Representative")
        _, allocation, _ = self._card(1, "MULTIPLE", rep)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("business_profile_preview"), {"allocation": allocation.pk})
        self.assertContains(response, "Selected Representative")
        other = User.objects.create_user("other-owner", password="test-password")
        other_business = BusinessProfile.objects.create(owner=other, name="Other Business")
        other_order = Order.objects.create(
            user=other, product=self.product, quantity=1, price=Decimal("900.00"),
            customer_name="Other", phone="01700000000", address="Dhaka", city="Dhaka",
            business_order_type="MULTIPLE", business_profile=other_business,
        )
        foreign_allocation = CardAllocation.objects.create(order=other_order, position=1)
        self.assertEqual(self.client.get(reverse("business_profile_preview"), {"allocation": foreign_allocation.pk}).status_code, 404)

    def test_offline_vcard_respects_owner_and_representative_contact_visibility(self):
        self.business.show_owner_identity = True
        self.business.save()
        _, _, single = self._card()
        vcard = build_vcard(single, offline=True)
        self.assertNotIn(self.profile.phone, vcard)
        self.assertNotIn(self.profile.email, vcard)
        self.profile.whatsapp = "8801700111222"
        self.profile.website = "https://personal.example"
        self.profile.address = "Private street"
        self.profile.facebook = "https://facebook.com/private"
        self.profile.save()
        self.business.share_owner_phone = True
        self.business.share_owner_whatsapp = True
        self.business.share_owner_website = True
        self.business.share_owner_address = True
        self.business.share_owner_social = True
        self.business.save()
        single.refresh_from_db()
        permitted_vcard = build_vcard(single, offline=True)
        for permitted_value in (self.profile.phone, self.profile.whatsapp, self.profile.website,
                                self.profile.address, self.profile.facebook):
            self.assertIn(permitted_value, permitted_vcard)
        self.assertNotIn(self.profile.email, permitted_vcard)
        rep = BusinessRepresentative.objects.create(
            business=self.business, name="Representative", phone="+8801999888777",
            email="rep@example.com", phone_public=True,
        )
        _, _, multiple = self._card(1, "MULTIPLE", rep)
        multiple_vcard = build_vcard(multiple, offline=True)
        self.assertIn("FN:Representative", multiple_vcard)
        self.assertIn("+8801999888777", multiple_vcard)
        self.assertNotIn("rep@example.com", multiple_vcard)
        self.assertNotIn(self.profile.phone, multiple_vcard)

    def test_personal_card_public_profile_remains_separate(self):
        personal = NFCCard.objects.create(card_uid="COMBINED-PERSONAL", owner=self.owner, status="ACTIVE")
        response = self.client.get(reverse("public_card", args=[personal.public_token]))
        self.assertContains(response, "Private Owner Name")
        self.assertNotContains(response, "NexTap Kitchen")
