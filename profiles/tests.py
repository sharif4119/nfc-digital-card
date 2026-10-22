from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import CardAllocation, Order
from products.models import Product
from profiles.forms import FeaturedOfferingForm
from profiles.models import BusinessProfile, FeaturedOffering, Profile


class PersonalProfileFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-customer", password="customer-pass",
        )
        self.client.force_login(self.user)
        self.data = {
            "display_username": "cardowner",
            "full_name": "Card Owner",
            "job_title": "Designer",
            "company": "Studio",
            "bio": "A short profile.",
            "phone": "+8801700000000",
            "email": "owner@example.com",
            "website": "arkitchen.pythonanywhere.com",
            "address": "Dhaka",
            "facebook": "facebook.com/cardowner",
            "instagram": "https://instagram.com/cardowner",
            "linkedin": "http://linkedin.com/in/cardowner",
            "whatsapp": "8801700000000",
            "github": "github.com/cardowner",
        }

    def test_private_profile_preview_renders_for_authenticated_user(self):
        profile = Profile.objects.get(user=self.user)
        profile.full_name = "Preview Name"
        profile.website = "https://example.com"
        profile.save()
        response = self.client.get(reverse("profile_preview"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profiles/profile_preview.html")
        self.assertContains(response, "Preview Name")
        self.assertContains(response, "Only you can see this page")

    def test_personal_profile_edit_and_preview_have_parent_navigation(self):
        edit_response = self.client.get(reverse("edit_profile"))
        self.assertContains(edit_response, reverse("dashboard"))
        preview_response = self.client.get(reverse("profile_preview"))
        self.assertContains(preview_response, reverse("edit_profile"))
        self.assertContains(preview_response, "Back to Edit Profile")

    def test_unauthenticated_preview_and_edit_redirect_to_login(self):
        self.client.logout()
        for route in ("profile_preview", "edit_profile"):
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response.url)

    def test_preview_recovers_when_customer_profile_record_is_missing(self):
        self.user.profile.delete()
        response = self.client.get(reverse("profile_preview"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_valid_profile_save_normalizes_urls_and_redirects_to_preview(self):
        response = self.client.post(reverse("edit_profile"), self.data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0][0], reverse("profile_preview"))
        self.assertContains(response, "Your personal profile was saved.")
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.full_name, "Card Owner")
        self.assertEqual(profile.website, "https://arkitchen.pythonanywhere.com")
        self.assertEqual(profile.facebook, "https://facebook.com/cardowner")
        self.assertEqual(profile.instagram, "https://instagram.com/cardowner")
        self.assertEqual(profile.linkedin, "http://linkedin.com/in/cardowner")
        self.assertEqual(profile.github, "https://github.com/cardowner")

    def test_personal_website_input_allows_server_side_normalization(self):
        response = self.client.get(reverse("edit_profile"))
        self.assertContains(response, 'type="text" name="website"')
        self.assertContains(response, 'inputmode="url"')

    def test_profile_save_with_uploaded_image(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), "blue").save(image_buffer, format="PNG")
        upload = SimpleUploadedFile(
            "portrait.png", image_buffer.getvalue(), content_type="image/png",
        )
        temp_root = Path(__file__).resolve().parents[1] / "tmp"
        with TemporaryDirectory(dir=temp_root, ignore_cleanup_errors=True) as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("edit_profile"),
                    {**self.data, "profile_picture": upload},
                )
                self.assertRedirects(response, reverse("profile_preview"))
                profile = Profile.objects.get(user=self.user)
                self.assertTrue(profile.profile_picture.name.endswith("portrait.png"))
                profile.profile_picture.delete(save=False)

    def test_malformed_personal_website_shows_field_error_and_keeps_input(self):
        response = self.client.post(
            reverse("edit_profile"),
            {**self.data, "website": "javascript:alert(1)"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a valid website address")
        self.assertContains(response, 'class="form-control is-invalid"')
        self.assertContains(response, "javascript:alert(1)")
        self.assertContains(response, "data-form-error-summary")


class BusinessProfileValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="business-customer", password="customer-pass",
        )
        self.client.force_login(self.user)
        self.data = {
            "name": "AR Kitchen",
            "description": "Home catering",
            "phone": "01700000000",
            "email": "hello@example.com",
            "website": "arkitchen.pythonanywhere.com",
            "address": "Dhaka",
            "facebook": "http://facebook.com/arkitchen",
            "instagram": "instagram.com/arkitchen",
            "linkedin": "https://linkedin.com/company/arkitchen",
            "whatsapp": "8801700000000",
            "offerings-TOTAL_FORMS": "6",
            "offerings-INITIAL_FORMS": "0",
            "offerings-MIN_NUM_FORMS": "0",
            "offerings-MAX_NUM_FORMS": "6",
        }

    def test_business_profile_saves_and_normalizes_bare_website_and_social_url(self):
        response = self.client.post(reverse("business_edit"), self.data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0][0], reverse("business_cards"))
        self.assertContains(response, "Your business profile was saved.")
        business = BusinessProfile.objects.get(owner=self.user)
        self.assertEqual(business.website, "https://arkitchen.pythonanywhere.com")
        self.assertEqual(business.facebook, "http://facebook.com/arkitchen")
        self.assertEqual(business.instagram, "https://instagram.com/arkitchen")
        self.assertEqual(business.linkedin, "https://linkedin.com/company/arkitchen")
        self.assertEqual(FeaturedOffering.objects.filter(business=business).count(), 0)

    def test_business_form_loads_with_custom_logo_controls_and_actions(self):
        response = self.client.get(reverse("business_edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Business Profile")
        self.assertContains(response, "Manage your business information and online presence.")
        self.assertContains(response, 'accept="image/*"')
        self.assertContains(response, "Save Business Profile")
        self.assertContains(response, "Save &amp; Preview")
        self.assertContains(response, 'name="logo"')
        self.assertContains(response, "Featured Products &amp; Services")
        self.assertContains(response, "Add up to six products or services to highlight on your profile.")
        self.assertNotContains(response, "remove_logo")
        self.assertNotContains(response, "Remove current logo")
        self.assertNotContains(response, "Clear")
        self.assertNotContains(response, "Currently:")
        self.assertContains(response, reverse("dashboard"))

    def test_existing_logo_is_not_shown_on_edit_form_but_is_available_in_preview(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), "blue").save(image_buffer, format="PNG")
        upload = SimpleUploadedFile("logo1.png", image_buffer.getvalue(), content_type="image/png")
        temp_root = Path(__file__).resolve().parents[1] / "tmp"
        with TemporaryDirectory(dir=temp_root, ignore_cleanup_errors=True) as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
                business.logo.save("logo1.png", upload, save=True)
                response = self.client.get(reverse("business_edit"))
                self.assertNotContains(response, "/media/business/logos/logo1.png")
                self.assertNotContains(response, "<img")
                self.assertNotContains(response, "Currently:")
                self.assertNotContains(response, "remove_logo")
                self.assertNotContains(response, "Remove current logo")
                self.assertNotContains(response, "Clear")
                preview_response = self.client.get(reverse("business_profile_preview"))
                self.assertContains(preview_response, "nxt-business-logo")
                self.assertContains(preview_response, "/media/business/logos/logo1.png")

    def test_missing_existing_logo_uses_placeholder(self):
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen", logo="business/logos/missing.png")
        response = self.client.get(reverse("business_edit"))
        self.assertNotContains(response, "nxt-business-logo")
        self.assertNotContains(response, "business/logos/missing.png")
        preview_response = self.client.get(reverse("business_profile_preview"))
        self.assertContains(preview_response, "nxt-business-logo-placeholder")
        save_response = self.client.post(reverse("business_edit"), self.data)
        self.assertRedirects(save_response, reverse("business_cards"))
        business.refresh_from_db()
        self.assertEqual(business.logo.name, "business/logos/missing.png")

    def test_logo_replacement_works_and_empty_upload_preserves_current_logo(self):
        image_buffer = BytesIO()
        Image.new("RGB", (3, 3), "blue").save(image_buffer, format="PNG")
        old_upload = SimpleUploadedFile("old.png", image_buffer.getvalue(), content_type="image/png")
        image_buffer = BytesIO()
        Image.new("RGB", (4, 4), "red").save(image_buffer, format="PNG")
        new_upload = SimpleUploadedFile("new.png", image_buffer.getvalue(), content_type="image/png")
        temp_root = Path(__file__).resolve().parents[1] / "tmp"
        with TemporaryDirectory(dir=temp_root, ignore_cleanup_errors=True) as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
                business.logo.save("old.png", old_upload, save=True)
                saved_logo_name = business.logo.name
                response = self.client.post(reverse("business_edit"), self.data)
                self.assertRedirects(response, reverse("business_cards"))
                business.refresh_from_db()
                self.assertEqual(business.logo.name, saved_logo_name)

                response = self.client.post(reverse("business_edit"), {**self.data, "logo": new_upload})
                self.assertRedirects(response, reverse("business_cards"))
                business.refresh_from_db()
                self.assertTrue(business.logo.name.endswith("new.png"))
                replaced_logo_name = business.logo.name

                response = self.client.post(reverse("business_edit"), self.data)
                self.assertRedirects(response, reverse("business_cards"))
                business.refresh_from_db()
                self.assertEqual(business.logo.name, replaced_logo_name)

    def test_existing_featured_offering_is_editable_in_its_own_formset_row(self):
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        offering = FeaturedOffering.objects.create(
            business=business, name="Saved service", description="Stored description",
        )

        response = self.client.get(reverse("business_edit"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="offerings-0-name"')
        self.assertContains(response, 'value="Saved service"')
        self.assertContains(response, 'value="Stored description"')
        self.assertEqual(FeaturedOffering.objects.get(pk=offering.pk).business_id, business.pk)

    def test_save_and_preview_saves_then_redirects_to_private_preview(self):
        response = self.client.post(reverse("business_edit"), {
            **self.data,
            "name": "NexTap Test Kitchen",
            "description": "Updated business description",
            "action": "preview",
            "offerings-0-name": "Catering service",
            "offerings-0-description": "Fresh meals for events",
            "offerings-0-external_url": "catering.example/menu",
            "offerings-0-position": "1",
        })
        self.assertRedirects(response, reverse("business_profile_preview"))
        business = BusinessProfile.objects.get(owner=self.user)
        self.assertEqual(business.name, "NexTap Test Kitchen")
        self.assertEqual(business.description, "Updated business description")
        offering = FeaturedOffering.objects.get(business=business)
        self.assertEqual(offering.name, "Catering service")
        self.assertEqual(offering.description, "Fresh meals for events")
        self.assertIsNone(offering.price)
        self.assertEqual(offering.external_url, "https://catering.example/menu")
        preview_response = self.client.get(response.url)
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, "Catering service")
        self.assertContains(preview_response, "Fresh meals for events")
        self.assertNotContains(preview_response, "1250.00")
        self.assertContains(preview_response, 'href="https://catering.example/menu"')
        self.assertContains(preview_response, "View Details")

    def test_offering_form_hides_price_and_existing_historical_price_is_preserved(self):
        self.assertNotIn("price", FeaturedOfferingForm().fields)
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        offering = FeaturedOffering.objects.create(
            business=business, name="Old service", description="Old details", price="1250.00",
        )
        post_data = {
            **self.data,
            "offerings-TOTAL_FORMS": "6",
            "offerings-INITIAL_FORMS": "1",
            "offerings-0-id": str(offering.pk),
            "offerings-0-name": "Updated service",
            "offerings-0-description": "Updated details",
            "offerings-0-external_url": "",
            "offerings-0-position": "1",
        }
        response = self.client.post(reverse("business_edit"), post_data)
        self.assertRedirects(response, reverse("business_cards"))
        offering.refresh_from_db()
        self.assertEqual(offering.name, "Updated service")
        self.assertEqual(str(offering.price), "1250.00")
        preview = self.client.get(reverse("business_profile_preview"))
        self.assertNotContains(preview, "1250.00")

    def test_business_type_and_education_subtype_use_dynamic_offering_labels(self):
        business = BusinessProfile.objects.create(
            owner=self.user, name="Example Institute", profile_type="ORGANIZATION",
            organization_category="EDUCATIONAL_INSTITUTE",
        )
        response = self.client.get(reverse("business_edit"))
        self.assertContains(response, "Organization Name")
        self.assertContains(response, "Academic Programs")
        self.assertContains(response, "Program Name")
        self.assertContains(response, "Program Details")
        self.assertContains(response, "Program Website / Learn More")
        self.assertNotContains(response, "price")
        self.assertEqual(business.owner_id, self.user.pk)

    def test_frontend_label_hooks_update_without_reloading(self):
        response = self.client.get(reverse("business_edit"))
        self.assertContains(response, 'data-business-profile-type=""')
        self.assertContains(response, 'data-organization-category=""')
        self.assertContains(response, 'src="/static/js/business-profile-form.js"')
        script = (Path(__file__).resolve().parents[1] / "static/js/business-profile-form.js").read_text()
        self.assertIn('typeSelect.addEventListener("change", update)', script)
        self.assertIn('categorySelect?.addEventListener("change", update)', script)
        self.assertIn('setText(`[data-dynamic-label="${key}"]`, value)', script)

    def test_organization_labels_are_correct_on_refresh_and_invalid_submission(self):
        BusinessProfile.objects.create(
            owner=self.user, name="Example Organization", profile_type="ORGANIZATION",
            organization_category="COMPANY",
        )
        response = self.client.get(reverse("business_edit"))
        self.assertContains(response, "Organization Name")
        self.assertContains(response, "Organization Description")
        self.assertContains(response, "Organization Contact Information")
        self.assertContains(response, "Products &amp; Services")
        invalid = self.client.post(reverse("business_edit"), {
            **self.data, "profile_type": "ORGANIZATION", "organization_category": "COMPANY",
            "website": "javascript:alert(1)",
        })
        self.assertEqual(invalid.status_code, 200)
        self.assertContains(invalid, "Organization Name")
        self.assertContains(invalid, "Organization Website")
        self.assertContains(invalid, '<option value="ORGANIZATION" selected')

    def test_education_preview_uses_academic_programs_and_only_learn_more_links(self):
        business = BusinessProfile.objects.create(
            owner=self.user, name="Example Institute", profile_type="ORGANIZATION",
            organization_category="EDUCATIONAL_INSTITUTE",
        )
        FeaturedOffering.objects.create(
            business=business, name="Computer Science", description="Undergraduate program",
            external_url="https://example.edu/programs/cs",
        )
        response = self.client.get(reverse("business_profile_preview"))
        self.assertContains(response, "Academic Programs")
        self.assertContains(response, "Computer Science")
        self.assertContains(response, "Undergraduate program")
        self.assertContains(response, "Learn More")
        self.assertNotContains(response, "View Details")
        self.assertNotContains(response, "Business owner")

    def test_offering_url_normalizes_safe_urls_and_rejects_unsafe_schemes(self):
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        good = {
            **self.data,
            "offerings-0-name": "Menu",
            "offerings-0-external_url": "https://example.com/menu",
            "offerings-0-position": "1",
        }
        response = self.client.post(reverse("business_edit"), good)
        self.assertEqual(response.status_code, 302, {
            "profile_errors": response.context["form"].errors if response.context else None,
            "offering_errors": response.context["offerings"].errors if response.context else None,
        })
        offering = FeaturedOffering.objects.get(business=business)
        self.assertEqual(offering.external_url, "https://example.com/menu")
        for bad_url in ("javascript:alert(1)", "data:text/html,hello", "//example.com"):
            with self.subTest(url=bad_url):
                response = self.client.post(reverse("business_edit"), {
                    **self.data,
                    "offerings-0-name": "Unsafe link",
                    "offerings-0-external_url": bad_url,
                    "offerings-0-position": "1",
                })
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Please enter a valid website address")
                self.assertContains(response, bad_url)

    def test_preview_link_only_appears_for_valid_saved_offering_url(self):
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        linked = FeaturedOffering.objects.create(
            business=business, name="Linked service", external_url="http://example.com/details",
        )
        plain = FeaturedOffering.objects.create(
            business=business, name="No link service", external_url="",
        )
        response = self.client.get(reverse("business_profile_preview"))
        self.assertContains(response, 'href="http://example.com/details"')
        self.assertContains(response, 'target="_blank" rel="noopener noreferrer"')
        self.assertContains(response, "View Details")
        self.assertNotContains(response, f'href="{plain.external_url}"')
        self.assertEqual(response.context["featured_offerings"].count(), 2)
        linked.external_url = "javascript:alert(1)"
        linked.save(update_fields=["external_url"])
        response = self.client.get(reverse("business_profile_preview"))
        self.assertNotContains(response, "View Details")
        self.assertNotContains(response, "javascript:alert(1)")

    def test_preview_context_contains_only_saved_featured_offerings(self):
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        saved_offering = FeaturedOffering.objects.create(
            business=business, name="Lunch box", description="Daily menu", price="250.00",
        )
        other = User.objects.create_user(username="unrelated-owner", password="customer-pass")
        other_business = BusinessProfile.objects.create(owner=other, name="Other business")
        FeaturedOffering.objects.create(business=other_business, name="Other owner offering")

        response = self.client.get(reverse("business_profile_preview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["featured_offerings"].model, FeaturedOffering)
        self.assertEqual(list(response.context["featured_offerings"]), [saved_offering])
        self.assertNotIn("offerings", response.context)

    def test_owner_name_is_not_rendered_as_an_offering_without_saved_offering(self):
        self.user.first_name = "Marcm"
        self.user.last_name = "Chowdhury"
        self.user.save(update_fields=["first_name", "last_name"])
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.full_name = "Marcm Chowdhury"
        profile.save(update_fields=["full_name"])

        response = self.client.get(reverse("business_profile_preview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["featured_offerings"]), [])
        self.assertContains(response, "No featured products or services added yet.")
        self.assertNotContains(response, "<h3>Marcm Chowdhury</h3>")
        self.assertEqual(business.offerings.count(), 0)

    def test_preview_shows_empty_state_and_keeps_business_layout_content(self):
        BusinessProfile.objects.create(
            owner=self.user, name="AR Kitchen", description="Home catering",
            phone="01700000000", email="hello@example.com", website="https://example.com",
            address="Dhaka",
        )
        response = self.client.get(reverse("business_profile_preview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No featured products or services added yet.")
        self.assertContains(response, "Explore More")
        self.assertContains(response, 'href="https://example.com"')
        self.assertContains(response, "nxt-business-identity")
        self.assertContains(response, "nxt-business-logo-column")
        self.assertContains(response, "nxt-business-details")

    def test_private_business_preview_shows_saved_profile_and_offerings_without_nfc_card(self):
        business = BusinessProfile.objects.create(
            owner=self.user, name="AR Kitchen", description="Fresh meals", email="hello@example.com",
            website="https://arkitchen.example", address="Dhaka", facebook="https://facebook.com/arkitchen",
        )
        FeaturedOffering.objects.create(business=business, name="Lunch box", description="Daily menu", price="250.00")
        response = self.client.get(reverse("business_profile_preview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AR Kitchen")
        self.assertContains(response, "Fresh meals")
        self.assertContains(response, "hello@example.com")
        self.assertContains(response, "Lunch box")
        self.assertContains(response, "Featured Products &amp; Services")
        self.assertContains(response, 'href="https://arkitchen.example"')
        self.assertContains(response, "Visit Business Website")
        self.assertContains(response, 'rel="noopener noreferrer"')
        self.assertNotContains(response, "Representative")
        self.assertNotContains(response, "Customer inquiries")
        self.assertNotContains(response, "৳250.00")

    def test_preview_omits_unsafe_or_missing_website_button(self):
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen", website="javascript:alert(1)")
        response = self.client.get(reverse("business_profile_preview"))
        self.assertNotContains(response, "Visit Website")
        business.website = ""
        business.save(update_fields=["website"])
        response = self.client.get(reverse("business_profile_preview"))
        self.assertNotContains(response, "Visit Website")

    def test_business_preview_requires_login_and_handles_missing_profile(self):
        self.client.logout()
        response = self.client.get(reverse("business_profile_preview"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.client.force_login(self.user)
        response = self.client.get(reverse("business_profile_preview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your business profile isn’t saved yet")

    def test_business_preview_only_shows_the_authenticated_owners_business(self):
        BusinessProfile.objects.create(owner=self.user, name="Private Business")
        other = User.objects.create_user(username="other-business-owner", password="test-password")
        self.client.force_login(other)
        response = self.client.get(reverse("business_profile_preview"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Private Business")
        self.assertContains(response, "Your business profile isn’t saved yet")

    def test_business_profile_pages_have_parent_navigation(self):
        BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        edit_response = self.client.get(reverse("business_edit"))
        self.assertContains(edit_response, reverse("dashboard"))
        preview_response = self.client.get(reverse("business_profile_preview"))
        self.assertContains(preview_response, reverse("business_cards"))
        self.assertContains(preview_response, reverse("business_edit"))
        cards_response = self.client.get(reverse("business_cards"))
        self.assertContains(cards_response, reverse("dashboard"))
        self.assertContains(cards_response, reverse("business_profile_preview"))
        self.assertContains(cards_response, "Preview Business Profile")
        self.assertContains(cards_response, "Edit Business Profile")
        self.assertContains(cards_response, 'class="bi bi-eye me-1"')
        preview_response = self.client.get(reverse("business_profile_preview"))
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.context["selected_card"], None)

    def test_cards_dashboard_preview_label_tracks_saved_organization_type(self):
        BusinessProfile.objects.create(
            owner=self.user, name="Example Organization", profile_type="ORGANIZATION",
        )
        response = self.client.get(reverse("business_cards"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preview Organization Profile")
        self.assertContains(response, reverse("business_profile_preview"))
        self.assertContains(response, "Edit Organization Profile")

    def test_cards_dashboard_keeps_representative_controls(self):
        business = BusinessProfile.objects.create(owner=self.user, name="AR Kitchen")
        product = Product.objects.create(name="Business NFC Card", price="500.00", card_category="BUSINESS")
        order = Order.objects.create(
            user=self.user, product=product, price="500.00", customer_name="Card Owner",
            phone="01700000000", address="Dhaka", city="Dhaka", business_profile=business,
            business_order_type="MULTIPLE", card_category="BUSINESS",
        )
        allocation = CardAllocation.objects.create(order=order, position=1)
        response = self.client.get(reverse("business_cards"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("representative_edit", args=[allocation.pk]))
        self.assertContains(response, "Edit person")

    def test_invalid_business_input_still_has_field_error_and_retained_value(self):
        response = self.client.post(reverse("business_edit"), {**self.data, "website": "javascript:alert(1)"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_website"')
        self.assertContains(response, "is-invalid")
        self.assertContains(response, "javascript:alert(1)")

    def test_http_and_https_urls_are_preserved(self):
        response = self.client.post(
            reverse("business_edit"),
            {**self.data, "website": "http://example.org/path", "facebook": "https://example.org/social"},
        )
        self.assertRedirects(response, reverse("business_cards"))
        business = BusinessProfile.objects.get(owner=self.user)
        self.assertEqual(business.website, "http://example.org/path")
        self.assertEqual(business.facebook, "https://example.org/social")

    def test_business_website_input_allows_server_side_normalization(self):
        response = self.client.get(reverse("business_edit"))
        self.assertContains(response, 'type="text" name="website"')
        self.assertContains(response, 'inputmode="url"')

    def test_malformed_unsafe_url_shows_summary_field_error_and_preserves_text(self):
        response = self.client.post(
            reverse("business_edit"),
            {**self.data, "website": "javascript:alert(1)"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a valid website address, such as https://example.com.")
        self.assertContains(response, "id=\"id_website\"")
        self.assertContains(response, "is-invalid")
        self.assertContains(response, "javascript:alert(1)")
        self.assertContains(response, "data-form-error-summary")
        self.assertFalse(BusinessProfile.objects.filter(owner=self.user).exists())

    def test_featured_offering_fieldset_error_is_shown_and_input_retained(self):
        response = self.client.post(
            reverse("business_edit"),
            {**self.data, "offerings-0-name": "N" * 151},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please review the highlighted fields.")
        self.assertContains(response, "Product / Service")
        self.assertContains(response, "N" * 151)
        self.assertContains(response, "is-invalid")
        self.assertFalse(BusinessProfile.objects.filter(owner=self.user).exists())

    def test_business_formset_management_errors_are_visible(self):
        response = self.client.post(
            reverse("business_edit"),
            {**self.data, "offerings-TOTAL_FORMS": "tampered"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please review the highlighted fields.")
        self.assertContains(response, "ManagementForm data is missing or has been tampered with")

    def test_normalization_rejects_malformed_values_without_rewriting_scheme(self):
        for website in ("//example.com", "https://", "ht!tp://bad", "data:text/html,hi"):
            with self.subTest(website=website):
                BusinessProfile.objects.filter(owner=self.user).delete()
                response = self.client.post(
                    reverse("business_edit"),
                    {**self.data, "website": website},
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Please enter a valid website address")
                self.assertFalse(BusinessProfile.objects.filter(owner=self.user).exists())
