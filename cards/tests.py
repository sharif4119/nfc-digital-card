from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import NFCCard


class PublicCardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-owner",
            password="test-password",
        )
        self.user.profile.full_name = "Profile Owner"
        self.user.profile.save(
            update_fields=["full_name"]
        )

    def test_inactive_card_public_url_returns_404(self):
        card = NFCCard.objects.create(
            card_uid="INACTIVE-001",
            owner=self.user,
            status="INACTIVE",
        )

        response = self.client.get(
            reverse(
                "public_card",
                args=[card.public_token],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_active_card_with_owner_profile_renders(self):
        card = NFCCard.objects.create(
            card_uid="ACTIVE-001",
            owner=self.user,
            status="ACTIVE",
        )

        response = self.client.get(
            reverse(
                "public_card",
                args=[card.public_token],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile Owner")
