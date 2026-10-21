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


class BusinessProfile(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="business_profile")
    name = models.CharField(max_length=150)
    logo = models.ImageField(upload_to="business/logos/", blank=True, null=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class BusinessRepresentative(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="representatives")
    name = models.CharField(max_length=150)
    designation = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class FeaturedOffering(models.Model):
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="offerings")
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=300, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="business/offerings/", blank=True, null=True)
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.name
