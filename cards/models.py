import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, models, transaction


def generate_public_token():
    return secrets.token_urlsafe(9)


class NFCCard(models.Model):
    STATUS_CHOICES = [
    ("UNASSIGNED", "Unassigned"),
    ("ASSIGNED", "Assigned"),
    ("PROGRAMMED", "Programmed"),
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
    programmed_at = models.DateTimeField(
    null=True,
    blank=True,
    )

    programmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programmed_nfc_cards",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    @classmethod
    def create_with_generated_uid(cls, **kwargs):
        """Create a card with a database-backed, human-readable unique UID."""
        with transaction.atomic():
            card = cls.objects.create(
                card_uid=f"PENDING-{secrets.token_hex(12)}",
                **kwargs,
            )
            generated_uids = (
                cls.objects.select_for_update()
                .filter(card_uid__startswith="NXT-")
                .exclude(pk=card.pk)
                .values_list("card_uid", flat=True)
            )
            used_numbers = [
                int(uid[4:])
                for uid in generated_uids
                if len(uid) == 10 and uid[4:].isdigit()
            ]
            sequence = max(used_numbers, default=0) + 1

            while sequence <= 999999:
                candidate = f"NXT-{sequence:06d}"
                try:
                    # Keep a rare uniqueness collision from breaking the
                    # surrounding card-preparation transaction.
                    with transaction.atomic():
                        cls.objects.filter(pk=card.pk).update(card_uid=candidate)
                except IntegrityError:
                    sequence += 1
                    continue

                card.card_uid = candidate
                return card

            raise RuntimeError("The automatic NFC card UID range is exhausted.")

    @property
    def public_url(self):
        return (
            f"{settings.PUBLIC_BASE_URL}"
            f"/c/{self.public_token}/"
        )

    def __str__(self):
        return f"{self.card_uid} - {self.status}"
