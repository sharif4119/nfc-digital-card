from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Lower


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    display_username = models.CharField(
        max_length=150,
        blank=True,
    )
    login_email = models.EmailField(
        blank=True,
        null=True,
    )

    full_name = models.CharField(max_length=150, blank=True)
    job_title = models.CharField(max_length=150, blank=True)
    company = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)

    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)

    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    github = models.URLField(blank=True)

    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("login_email"),
                condition=models.Q(login_email__isnull=False),
                name="profile_login_email_ci_unique",
            ),
        ]

    @property
    def account_name(self):
        return (
            self.display_username
            or self.full_name
            or self.user.username
        )

    @property
    def public_name(self):
        return (
            self.full_name
            or self.display_username
            or self.user.username
        )

    def __str__(self):
        return self.public_name
