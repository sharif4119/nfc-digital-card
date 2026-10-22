from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlsplit

from django.forms import inlineformset_factory

from .models import Profile, BusinessProfile, BusinessRepresentative, FeaturedOffering


WEB_URL_ERROR = _(
    "Please enter a valid website address, such as https://example.com."
)
_validate_web_url = URLValidator(schemes=["http", "https"])


def normalize_web_url(value):
    """Normalize a valid bare web host to HTTPS and reject unsafe schemes."""
    value = (value or "").strip()
    if not value:
        return value
    if any(character.isspace() for character in value) or "\\" in value:
        raise ValidationError(WEB_URL_ERROR)

    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValidationError(WEB_URL_ERROR) from exc
    if parsed.scheme:
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValidationError(WEB_URL_ERROR)
        normalized = value
    else:
        # Scheme-relative URLs and malformed host/path values are not domains.
        if value.startswith("//") or not parsed.path:
            raise ValidationError(WEB_URL_ERROR)
        normalized = f"https://{value}"

    try:
        parsed = urlsplit(normalized)
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValidationError(WEB_URL_ERROR)
        _validate_web_url(normalized)
    except (ValueError, ValidationError) as exc:
        raise ValidationError(WEB_URL_ERROR) from exc
    return normalized


def add_field_error_styles(form):
    for name, field in form.fields.items():
        if name in form.errors:
            field.widget.attrs["class"] = (
                field.widget.attrs.get("class", "") + " is-invalid"
            ).strip()
            field.widget.attrs["aria-invalid"] = "true"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile

        fields = [
            "profile_picture",
            "display_username",
            "full_name",
            "job_title",
            "company",
            "bio",
            "phone",
            "email",
            "website",
            "address",
            "facebook",
            "instagram",
            "linkedin",
            "whatsapp",
            "github",
        ]

        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "rows": 4,
                }
            ),
        }
    def clean_profile_picture(self):
        image = self.cleaned_data.get("profile_picture")

        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "Profile picture must be under 5 MB."
            )

        return image

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            if isinstance(field, forms.URLField):
                field.error_messages["invalid"] = WEB_URL_ERROR
                # HTML's native type=url rejects valid bare domains before
                # the server can normalize them, so use text with URL hints.
                field.widget.input_type = "text"
                field.widget.attrs.update({
                    "inputmode": "url",
                    "placeholder": "example.com or https://example.com",
                })
        add_field_error_styles(self)

    def _clean_web_field(self, field_name):
        # URLField normally prepends an assumed scheme before form-level
        # cleaners run, so validate and normalize the submitted text itself.
        submitted = self.data.get(self.add_prefix(field_name), "")
        return normalize_web_url(submitted)

    def clean_website(self):
        return self._clean_web_field("website")

    def clean_facebook(self):
        return self._clean_web_field("facebook")

    def clean_instagram(self):
        return self._clean_web_field("instagram")

    def clean_linkedin(self):
        return self._clean_web_field("linkedin")

    def clean_github(self):
        return self._clean_web_field("github")

    def clean_phone(self):
        phone = self.cleaned_data.get(
            "phone",
            "",
        ).strip()

        if not phone:
            return phone

        cleaned = (
            phone.replace("+", "")
            .replace("-", "")
            .replace(" ", "")
        )

        if not cleaned.isdigit():
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        return phone

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get(
            "whatsapp",
            "",
        ).strip()

        if not whatsapp:
            return whatsapp

        cleaned = (
            whatsapp.replace("+", "")
            .replace("-", "")
            .replace(" ", "")
        )

        if not cleaned.isdigit():
            raise forms.ValidationError(
                "Enter WhatsApp number using digits only."
            )

        if len(cleaned) < 10 or len(cleaned) > 15:
            raise forms.ValidationError(
                "Enter a valid WhatsApp number."
            )

        return cleaned


class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = [
            "profile_type", "organization_category", "name", "logo", "banner",
            "description", "phone", "email", "website", "address",
            "facebook", "instagram", "linkedin", "whatsapp",
            "show_owner_identity", "share_owner_phone", "share_owner_email",
            "share_owner_whatsapp", "share_owner_website", "share_owner_address",
            "share_owner_social",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            # Use a plain file input so Django never renders a stored path or
            # a default ClearableFileInput checkbox for an existing logo.
            "logo": forms.FileInput(attrs={"accept": "image/*"}),
            "banner": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Existing/manual POST clients may not submit the newly additive
        # selectors; preserve the row's current value or the migration default.
        self.fields["profile_type"].required = False
        self.fields["organization_category"].required = False
        self.fields["profile_type"].initial = self.instance.profile_type or "SMALL_BUSINESS"
        self.fields["organization_category"].initial = self.instance.organization_category or "COMPANY"
        profile_type = self.data.get(self.add_prefix("profile_type")) or self.instance.profile_type or "SMALL_BUSINESS"
        organization_category = self.data.get(self.add_prefix("organization_category")) or self.instance.organization_category or "COMPANY"
        organization = profile_type == "ORGANIZATION"
        self.fields["name"].label = "Organization Name" if organization else "Business Name"
        self.fields["logo"].label = "Organization Logo" if organization else "Business Logo"
        self.fields["description"].label = "Organization Description" if organization else "Business Description"
        self.fields["website"].label = "Organization Website" if organization else "Business Website"
        self.fields["phone"].label = "Organization Phone" if organization else "Business Phone"
        self.fields["email"].label = "Organization Email" if organization else "Business Email"
        self.fields["address"].label = "Organization Address" if organization else "Business Address"
        self.profile_type = profile_type
        self.organization_category = organization_category
        self.fields["name"].widget.attrs["placeholder"] = (
            "Organization or institute name" if organization else "e.g. AR Kitchen"
        )
        self.fields["profile_type"].widget.attrs["data-business-profile-type"] = ""
        self.fields["organization_category"].widget.attrs["data-organization-category"] = ""
        for name in ("show_owner_identity", "share_owner_phone", "share_owner_email",
                     "share_owner_whatsapp", "share_owner_website", "share_owner_address",
                     "share_owner_social"):
            self.fields[name].widget.attrs["class"] = "form-check-input"
        self.fields["banner"].help_text = "Optional organization cover image · up to 5 MB"
        self.fields["show_owner_identity"].label = "Show Personal/Representative Information"
        self.fields["show_owner_identity"].help_text = (
            "Display the owner or assigned representative above your business or organization details."
        )
        self.fields["share_owner_phone"].label = "Share my personal phone"
        self.fields["share_owner_email"].label = "Share my personal email"
        self.fields["share_owner_whatsapp"].label = "Share my personal WhatsApp"
        self.fields["share_owner_website"].label = "Share my personal website"
        self.fields["share_owner_address"].label = "Share my personal address"
        self.fields["share_owner_social"].label = "Share my personal social links"
        self.fields["description"].widget.attrs["placeholder"] = (
            "A short introduction to your organization" if organization
            else "A short introduction to your business and what you offer"
        )
        self.fields["phone"].widget.attrs["placeholder"] = "+880 1XXX-XXXXXX"
        self.fields["email"].widget.attrs["placeholder"] = "hello@yourbusiness.com"
        self.fields["address"].widget.attrs["placeholder"] = "Street, area, city"
        self.fields["website"].widget.attrs["placeholder"] = (
            "yourorganization.com" if organization else "yourbusiness.com"
        )
        self.fields["facebook"].widget.attrs["placeholder"] = "facebook.com/yourbusiness"
        self.fields["instagram"].widget.attrs["placeholder"] = "instagram.com/yourbusiness"
        self.fields["linkedin"].widget.attrs["placeholder"] = "linkedin.com/company/yourbusiness"
        self.fields["whatsapp"].widget.attrs.update({"placeholder": "8801XXXXXXXXX", "inputmode": "tel"})
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-check-input" if isinstance(field, forms.BooleanField) else "form-control"
            )
            if isinstance(field, forms.URLField):
                field.error_messages["invalid"] = WEB_URL_ERROR
                field.widget.input_type = "text"
                field.widget.attrs.update({
                    "inputmode": "url",
                })
        add_field_error_styles(self)

    def _clean_web_field(self, field_name):
        submitted = self.data.get(self.add_prefix(field_name), "")
        return normalize_web_url(submitted)

    def clean_website(self):
        return self._clean_web_field("website")

    def clean_profile_type(self):
        return self.cleaned_data.get("profile_type") or (self.instance.profile_type if self.instance.pk else "SMALL_BUSINESS")

    def clean_organization_category(self):
        return self.cleaned_data.get("organization_category") or (self.instance.organization_category if self.instance.pk else "COMPANY")

    def clean_facebook(self):
        return self._clean_web_field("facebook")

    def clean_instagram(self):
        return self._clean_web_field("instagram")

    def clean_linkedin(self):
        return self._clean_web_field("linkedin")

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and "logo" in self.files and logo.size > 5 * 1024 * 1024:
            noun = "Organization logo" if self.profile_type == "ORGANIZATION" else "Business logo"
            raise forms.ValidationError(f"{noun} must be under 5 MB.")
        return logo

    def clean_banner(self):
        banner = self.cleaned_data.get("banner")
        if banner and "banner" in self.files and banner.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Banner must be under 5 MB.")
        return banner

    def clean_whatsapp(self):
        value = self.cleaned_data.get("whatsapp", "").strip()
        normalized = value.replace("+", "").replace("-", "").replace(" ", "")
        if normalized and (not normalized.isdigit() or not 10 <= len(normalized) <= 15):
            raise forms.ValidationError("Enter a valid WhatsApp number.")
        return normalized


class FeaturedOfferingForm(forms.ModelForm):
    class Meta:
        model = FeaturedOffering
        fields = ["name", "description", "image", "external_url", "position"]

    def __init__(self, *args, **kwargs):
        self.profile_type = kwargs.pop("profile_type", "SMALL_BUSINESS")
        self.organization_category = kwargs.pop("organization_category", "COMPANY")
        super().__init__(*args, **kwargs)
        is_education = (
            self.profile_type == "ORGANIZATION"
            and self.organization_category == "EDUCATIONAL_INSTITUTE"
        )
        if is_education:
            self.fields["name"].label = "Program Name"
            self.fields["description"].label = "Program Details"
            self.fields["external_url"].label = "Program Website / Learn More"
        elif self.profile_type == "ORGANIZATION":
            self.fields["name"].label = "Product / Service Name"
            self.fields["description"].label = "Description / Details"
            self.fields["external_url"].label = "More Information Link"
        else:
            self.fields["name"].label = "Product / Service Name"
            self.fields["description"].label = "Description / Details"
            self.fields["external_url"].label = "More Information Link"
        self.fields["external_url"].error_messages["invalid"] = WEB_URL_ERROR
        self.fields["external_url"].widget.input_type = "text"
        self.fields["external_url"].widget.attrs.update({
            "inputmode": "url",
            "placeholder": "https://example.com or example.com",
        })
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def has_changed(self):
        # The position field's model default can make an otherwise blank
        # extra row look changed. Treat rows with no entered offering data as
        # empty, while still validating partially completed rows.
        if self.empty_permitted:
            value_fields = ("name", "description", "external_url")
            has_value = any(
                self.data.get(self.add_prefix(name), "").strip()
                for name in value_fields
            ) or bool(self.files.get(self.add_prefix("image")))
            is_deleted = bool(self.data.get(self.add_prefix("DELETE")))
            if not has_value and not is_deleted:
                return False
        return super().has_changed()

    def clean_external_url(self):
        submitted = self.data.get(
            self.add_prefix("external_url"), self.cleaned_data.get("external_url", "")
        )
        return normalize_web_url(submitted)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image must be under 5 MB.")
        return image


FeaturedOfferingFormSet = inlineformset_factory(
    BusinessProfile, FeaturedOffering, form=FeaturedOfferingForm,
    extra=6, max_num=6, validate_max=True, can_delete=True,
)


class RepresentativeForm(forms.ModelForm):
    class Meta:
        model = BusinessRepresentative
        fields = ["name", "designation", "bio", "photo", "phone", "phone_public", "email", "email_public"]
        widgets = {"photo": forms.FileInput(attrs={"accept": "image/*"}),
                   "bio": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-check-input" if isinstance(field, forms.BooleanField) else "form-control"

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and "photo" in self.files and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Representative photo must be under 5 MB.")
        return photo
