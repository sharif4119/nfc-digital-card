from email.mime import image

from django import forms

from django.forms import inlineformset_factory

from .models import Profile, BusinessProfile, BusinessRepresentative, FeaturedOffering


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
        fields = ["name", "logo", "description", "phone", "email", "website", "address", "facebook", "instagram", "linkedin", "whatsapp"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and logo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Logo must be under 5 MB.")
        return logo

    def clean_whatsapp(self):
        value = self.cleaned_data.get("whatsapp", "").strip()
        normalized = value.replace("+", "").replace("-", "").replace(" ", "")
        if normalized and (not normalized.isdigit() or not 10 <= len(normalized) <= 15):
            raise forms.ValidationError("Enter a valid WhatsApp number.")
        return normalized


class FeaturedOfferingForm(forms.ModelForm):
    class Meta:
        model = FeaturedOffering
        fields = ["name", "description", "price", "image", "position"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

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
        fields = ["name", "designation", "phone", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
