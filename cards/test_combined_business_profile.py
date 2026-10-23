from decimal import Decimal
from unittest.mock import patch

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
            "show_owner_identity": "on",
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
        self.assertContains(preview, "Assign a representative to this card to include their details in the preview.")
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
        self.assertContains(response, "Founder")
        self.assertNotContains(response, "+8801700111222")
        self.assertNotContains(response, "private@example.com")
        self.assertNotContains(response, "Account Purchaser")

    def test_combined_identity_is_only_a_summary_without_personal_contacts(self):
        self.business.show_owner_identity = True
        self.business.save()
        self.profile.bio = "A short public introduction."
        self.profile.whatsapp = "8801800222333"
        self.profile.address = "Private home address"
        self.profile.facebook = "https://facebook.com/private-owner"
        self.profile.save()
        self.business.share_owner_phone = True
        self.business.share_owner_email = True
        self.business.share_owner_whatsapp = True
        self.business.share_owner_address = True
        self.business.share_owner_social = True
        self.business.save()
        _, _, card = self._card()

        response = self.client.get(reverse("public_card", args=[card.public_token]))
        body = response.content.decode()
        summary = body.split('<section class="nxt-person-identity"', 1)[1].split("</section>", 1)[0]
        self.assertIn("Private Owner Name", summary)
        self.assertIn("Founder", summary)
        self.assertIn("A short public introduction.", summary)
        for private_value in (
            "+8801700111222", "private@example.com", "8801800222333",
            "Private home address", "private-owner",
        ):
            self.assertNotIn(private_value, summary)
        self.assertNotContains(response, "nxt-person-contacts")
        self.assertNotContains(response, "nxt-person-socials")

    def test_private_preview_links_owner_identity_to_existing_personal_preview(self):
        self.business.show_owner_identity = True
        self.business.save()
        self.client.force_login(self.owner)

        response = self.client.get(reverse("business_profile_preview"))

        self.assertContains(response, "View Personal Profile")
        self.assertContains(response, f'href="{reverse("profile_preview")}"')

    def test_public_owner_button_uses_business_card_person_route_without_a_personal_card(self):
        self.business.show_owner_identity = True
        self.business.save()
        _, _, business_card = self._card()
        visible = self.client.get(reverse("public_card", args=[business_card.public_token]))
        self.assertContains(visible, "View Personal Profile")
        person_url = reverse("public_person_profile", args=[business_card.public_token])
        self.assertContains(visible, f'href="{person_url}"')

        # No visitor login and no separate Personal NFC Card are required.
        person_page = self.client.get(person_url)
        self.assertEqual(person_page.status_code, 200)
        self.assertContains(person_page, "Private Owner Name")
        self.assertContains(person_page, "Back to Business Profile")
        self.assertContains(person_page, f'href="{reverse("public_card", args=[business_card.public_token])}"')
        self.assertNotContains(person_page, "/profile/preview/")

    def test_public_person_details_obey_each_owner_contact_privacy_setting(self):
        self.business.show_owner_identity = True
        self.business.share_owner_phone = True
        self.business.share_owner_email = False
        self.business.share_owner_whatsapp = False
        self.business.share_owner_website = False
        self.business.share_owner_address = False
        self.business.share_owner_social = False
        self.business.save()
        self.profile.whatsapp = "8801800222333"
        self.profile.website = "https://private.example.test"
        self.profile.address = "Private owner address"
        self.profile.facebook = "https://facebook.com/private-owner"
        self.profile.save()
        _, _, card = self._card()

        response = self.client.get(reverse("public_person_profile", args=[card.public_token]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "+8801700111222")
        for hidden_value in (
            "private@example.com", "8801800222333", "private.example.test",
            "Private owner address", "private-owner",
        ):
            self.assertNotContains(response, hidden_value)

    def test_public_person_details_hidden_when_identity_sharing_is_off(self):
        _, _, card = self._card()
        business_page = self.client.get(reverse("public_card", args=[card.public_token]))
        self.assertNotContains(business_page, "View Personal Profile")
        self.assertEqual(
            self.client.get(reverse("public_person_profile", args=[card.public_token])).status_code,
            404,
        )

    def test_inactive_business_card_cannot_expose_person_details(self):
        _, _, card = self._card(status="INACTIVE")
        self.business.show_owner_identity = True
        self.business.save()
        self.assertEqual(
            self.client.get(reverse("public_person_profile", args=[card.public_token])).status_code,
            404,
        )

    def test_public_multiple_person_pages_use_only_the_card_representative(self):
        self.business.show_owner_identity = True
        self.business.save()
        first_rep = BusinessRepresentative.objects.create(
            business=self.business, name="Card One Representative", designation="Manager",
            phone="01711111111", email="one@example.test", phone_public=True, email_public=True,
        )
        second_rep = BusinessRepresentative.objects.create(
            business=self.business, name="Card Two Representative", designation="Director",
            phone="01722222222", email="two@example.test", phone_public=True, email_public=True,
        )
        _, _, first_card = self._card(1, "MULTIPLE", first_rep)
        _, _, second_card = self._card(2, "MULTIPLE", second_rep)

        first_page = self.client.get(reverse("public_person_profile", args=[first_card.public_token]))
        second_page = self.client.get(reverse("public_person_profile", args=[second_card.public_token]))
        first_business_page = self.client.get(reverse("public_card", args=[first_card.public_token]))
        second_business_page = self.client.get(reverse("public_card", args=[second_card.public_token]))

        self.assertContains(first_business_page, f'href="{reverse("public_person_profile", args=[first_card.public_token])}"')
        self.assertContains(second_business_page, f'href="{reverse("public_person_profile", args=[second_card.public_token])}"')
        self.assertContains(first_page, "Card One Representative")
        self.assertContains(first_page, "one@example.test")
        self.assertNotContains(first_page, "Card Two Representative")
        self.assertNotContains(first_page, "Private Owner Name")
        self.assertContains(second_page, "Card Two Representative")
        self.assertContains(second_page, "two@example.test")
        self.assertNotContains(second_page, "Card One Representative")

    def test_public_organization_person_page_uses_assigned_representative(self):
        self.business.profile_type = "ORGANIZATION"
        self.business.show_owner_identity = True
        self.business.save()
        rep = BusinessRepresentative.objects.create(
            business=self.business, name="Institute Representative", designation="Principal",
            bio="Institute contact", email="principal@example.test", email_public=True,
        )
        _, _, card = self._card(rep=rep)

        business_page = self.client.get(reverse("public_card", args=[card.public_token]))
        response = self.client.get(reverse("public_person_profile", args=[card.public_token]))

        self.assertContains(business_page, f'href="{reverse("public_person_profile", args=[card.public_token])}"')
        self.assertContains(response, "Institute Representative")
        self.assertContains(response, "Principal")
        self.assertContains(response, "principal@example.test")
        self.assertNotContains(response, "Private Owner Name")

    def test_missing_representative_hides_button_and_person_route_returns_404(self):
        self.business.profile_type = "ORGANIZATION"
        self.business.show_owner_identity = True
        self.business.save()
        _, _, card = self._card()

        business_page = self.client.get(reverse("public_card", args=[card.public_token]))

        self.assertNotContains(business_page, "View Personal Profile")
        self.assertEqual(
            self.client.get(reverse("public_person_profile", args=[card.public_token])).status_code,
            404,
        )

    def test_public_representative_button_uses_card_person_page_not_owner_page(self):
        self.business.profile_type = "ORGANIZATION"
        self.business.show_owner_identity = True
        self.business.save()
        representative = BusinessRepresentative.objects.create(business=self.business, name="Organization Representative")
        _, _, card = self._card(rep=representative)
        NFCCard.objects.create(
            card_uid="REPRESENTATIVE-OWNER-PERSONAL", owner=self.owner, status="ACTIVE",
        )

        response = self.client.get(reverse("public_card", args=[card.public_token]))

        self.assertContains(response, "Organization Representative")
        person_url = reverse("public_person_profile", args=[card.public_token])
        self.assertContains(response, "View Personal Profile")
        self.assertContains(response, f'href="{person_url}"')
        person_page = self.client.get(person_url)
        self.assertContains(person_page, "Organization Representative")
        self.assertNotContains(person_page, "Private Owner Name")

    def test_business_multiple_cards_use_only_their_own_representatives(self):
        self.business.show_owner_identity = True
        self.business.save()
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
        self.business.show_owner_identity = True
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
        self.assertNotContains(response, "principal@example.edu")
        self.assertNotContains(response, "Private Owner Name")

    def test_public_business_page_has_no_empty_banner_or_generic_whatsapp_shortcut(self):
        self.business.phone = "01700000001"
        self.business.whatsapp = "8801700000001"
        self.business.save()
        _, _, card = self._card()

        response = self.client.get(reverse("public_card", args=[card.public_token]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "profile-cover")
        self.assertNotContains(response, "nxt-org-cover-placeholder")
        self.assertNotContains(response, "whatsapp-float")
        self.assertNotContains(response, "8801610395999")
        self.assertNotContains(response, "nxt-person-identity")
        self.assertContains(response, "nxt-business-identity")
        self.assertContains(response, "wa.me/8801700000001")

    def test_public_organization_page_has_no_empty_banner_but_keeps_logo_section(self):
        self.business.profile_type = "ORGANIZATION"
        self.business.organization_category = "COMPANY"
        self.business.show_owner_identity = True
        self.business.save()
        rep = BusinessRepresentative.objects.create(business=self.business, name="Assigned Representative")
        _, _, card = self._card(rep=rep)

        response = self.client.get(reverse("public_card", args=[card.public_token]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned Representative")
        self.assertContains(response, "nxt-business-logo-column")
        self.assertNotContains(response, "nxt-org-cover-placeholder")
        self.assertNotContains(response, "profile-cover")
        self.assertNotContains(response, "whatsapp-float")
        self.assertNotContains(response, "Private Owner Name")

    def test_offline_contact_qr_contains_vcard_data_and_not_only_a_url(self):
        self.profile.full_name = "Public Person"
        self.profile.phone = "+8801700111222"
        self.profile.email = "person@example.com"
        self.profile.save()
        card = NFCCard.objects.create(
            card_uid="PERSONAL-OFFLINE-QR", owner=self.owner, status="ACTIVE",
        )

        with patch("cards.views.qrcode.make", wraps=__import__("qrcode").make) as make_qr:
            response = self.client.get(reverse("offline_contact_qr", args=[card.public_token]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        payload = make_qr.call_args.args[0]
        self.assertIn("BEGIN:VCARD", payload)
        self.assertIn("FN:Public Person", payload)
        self.assertIn("TEL:+8801700111222", payload)
        self.assertIn("EMAIL:person@example.com", payload)
        self.assertIn(card.public_url, payload)
        self.assertNotEqual(payload, card.public_url)

    def test_personal_identity_setting_defaults_off_and_editor_explains_it(self):
        self.assertFalse(self.business.show_owner_identity)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("business_edit"))
        self.assertContains(response, "Show Personal/Representative Information")
        self.assertContains(response, "Display the owner or assigned representative above your business or organization details.")
        self.business.profile_type = "ORGANIZATION"
        self.business.save()
        organization_editor = self.client.get(reverse("business_edit"))
        self.assertContains(organization_editor, "Show Personal/Representative Information")

    def test_business_identity_is_omitted_and_business_is_first_when_visibility_is_off(self):
        self.business.phone = "01700000001"
        self.business.save()
        _, _, card = self._card()
        response = self.client.get(reverse("public_card", args=[card.public_token]))
        body = response.content.decode()
        self.assertNotContains(response, "nxt-person-identity")
        self.assertNotContains(response, "Identity not set yet")
        self.assertNotContains(response, "Representative details will appear")
        self.assertLess(body.index("nxt-business-identity"), body.index('<h2 id="nxt-business-name">'))
        self.assertContains(response, "01700000001")

    def test_identity_toggle_on_but_missing_person_has_no_public_placeholder(self):
        self.business.show_owner_identity = True
        self.business.save()
        self.profile.full_name = ""
        self.profile.save()
        _, _, card = self._card()
        response = self.client.get(reverse("public_card", args=[card.public_token]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "nxt-person-identity")
        self.assertNotContains(response, "Identity not set yet")
        self.client.force_login(self.owner)
        preview = self.client.get(reverse("business_profile_preview"))
        self.assertContains(preview, "Add your full name to your Personal Profile")

    def test_business_multiple_visibility_off_hides_assigned_representative(self):
        self.business.show_owner_identity = False
        self.business.save()
        rep = BusinessRepresentative.objects.create(
            business=self.business, name="Assigned Rep Hidden", phone="+8801999888777", phone_public=True,
        )
        _, _, card = self._card(1, "MULTIPLE", rep)
        response = self.client.get(reverse("public_card", args=[card.public_token]))
        self.assertNotContains(response, "Assigned Rep Hidden")
        self.assertNotContains(response, "nxt-person-identity")
        vcard = build_vcard(card, offline=True)
        self.assertNotIn("Assigned Rep Hidden", vcard)
        self.assertNotIn("+8801999888777", vcard)
        self.assertIn("ORG:NexTap Kitchen", vcard)

    def test_company_and_educational_profiles_use_the_same_optional_identity_setting(self):
        rep = BusinessRepresentative.objects.create(business=self.business, name="Org Representative")
        _, _, card = self._card(rep=rep)
        for category in ("COMPANY", "EDUCATIONAL_INSTITUTE"):
            with self.subTest(category=category):
                self.business.profile_type = "ORGANIZATION"
                self.business.organization_category = category
                self.business.show_owner_identity = False
                self.business.save()
                hidden = self.client.get(reverse("public_card", args=[card.public_token]))
                self.assertNotContains(hidden, "Org Representative")
                self.business.show_owner_identity = True
                self.business.save()
                visible = self.client.get(reverse("public_card", args=[card.public_token]))
                self.assertContains(visible, "Org Representative")

    def test_offline_vcard_never_contains_owner_identity_when_toggle_is_off(self):
        self.profile.full_name = "Hidden Owner Identity"
        self.profile.phone = "+8801700111222"
        self.profile.email = "private@example.com"
        self.profile.save()
        self.business.phone = "+88025551234"
        self.business.email = "office@example.com"
        self.business.save()
        _, _, card = self._card()
        vcard = build_vcard(card, offline=True)
        self.assertNotIn("Hidden Owner Identity", vcard)
        self.assertNotIn("+8801700111222", vcard)
        self.assertNotIn("private@example.com", vcard)
        self.assertIn("ORG:NexTap Kitchen", vcard)
        self.assertIn("office@example.com", vcard)
        self.assertIn(card.public_url, vcard)

    def test_organization_contact_qr_uses_its_assigned_representative_and_public_work_contacts(self):
        self.business.profile_type = "ORGANIZATION"
        self.business.show_owner_identity = True
        self.business.phone = "+88025551234"
        self.business.email = "office@example.edu"
        self.business.address = "Official Campus"
        self.business.save()
        rep = BusinessRepresentative.objects.create(
            business=self.business, name="Assigned Principal", designation="Principal",
            phone="+8801999888777", email="principal@example.edu", phone_public=True,
            email_public=False,
        )
        order, allocation, card = self._card(rep=rep)

        vcard = build_vcard(card, offline=True)

        self.assertIn("FN:Assigned Principal", vcard)
        self.assertIn("TITLE:Principal", vcard)
        self.assertIn("ORG:NexTap Kitchen", vcard)
        self.assertIn("TEL;TYPE=WORK:+8801999888777", vcard)
        self.assertNotIn("principal@example.edu", vcard)
        self.assertIn("office@example.edu", vcard)
        self.assertIn("Official Campus", vcard)
        self.assertIn(card.public_url, vcard)
        self.assertNotIn("Account Purchaser", vcard)
        self.assertNotIn("Private Owner Name", vcard)
        self.assertEqual(allocation.representative, rep)

    def test_offline_contact_snapshots_differ_for_distinct_representatives(self):
        self.business.show_owner_identity = True
        self.business.save()
        first_rep = BusinessRepresentative.objects.create(
            business=self.business, name="First Snapshot", phone="01711111111", phone_public=True,
        )
        second_rep = BusinessRepresentative.objects.create(
            business=self.business, name="Second Snapshot", phone="01722222222", phone_public=True,
        )
        _, _, first_card = self._card(1, "MULTIPLE", first_rep)
        _, _, second_card = self._card(2, "MULTIPLE", second_rep)

        first_vcard = build_vcard(first_card, offline=True)
        second_vcard = build_vcard(second_card, offline=True)

        self.assertIn("FN:First Snapshot", first_vcard)
        self.assertIn("01711111111", first_vcard)
        self.assertNotIn("Second Snapshot", first_vcard)
        self.assertIn("FN:Second Snapshot", second_vcard)
        self.assertIn("01722222222", second_vcard)
        self.assertNotIn("First Snapshot", second_vcard)

    def test_personal_offline_vcard_escapes_unicode_and_folds_by_utf8_octets(self):
        self.profile.full_name = "শাহরিয়ার, মিয়া; NexTap"
        self.profile.bio = "যোগাযোগের জন্য স্বাগতম " * 12
        self.profile.save()
        self.owner.refresh_from_db()
        card = NFCCard.objects.create(
            card_uid="PERSONAL-UNICODE-VCARD", owner=self.owner, status="ACTIVE",
        )

        vcard = build_vcard(card, offline=True)
        lines = vcard.rstrip("\r\n").split("\r\n")

        self.assertIn("FN:শাহরিয়ার\\, মিয়া\\; NexTap", vcard)
        self.assertIn(card.public_url, vcard)
        self.assertLessEqual(max(len(line.encode("utf-8")) for line in lines), 75)
        continuation_lines = [line for line in lines if line.startswith(" ")]
        self.assertTrue(continuation_lines)

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
        self.assertNotContains(response, "View Personal Profile")
