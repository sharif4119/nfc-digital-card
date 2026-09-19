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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"