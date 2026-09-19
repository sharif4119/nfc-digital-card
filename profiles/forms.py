from email.mime import image

from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile

        fields = [
            "profile_picture",
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