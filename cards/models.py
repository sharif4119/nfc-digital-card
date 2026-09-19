import secrets

from django.contrib.auth.models import User
from django.db import models


def generate_public_token():
    return secrets.token_urlsafe(6)


class NFCCard(models.Model):
    STATUS_CHOICES = [
        ("UNASSIGNED", "Unassigned"),
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    ]

    card_uid = models.CharField(
        max_length=50,
        unique=True,
    )

    public_token = models.CharField(
        max_length=30,
        unique=True,
        default=generate_public_token,
        editable=False,
    )

    owner = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nfc_card",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="UNASSIGNED",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.card_uid} - {self.status}"