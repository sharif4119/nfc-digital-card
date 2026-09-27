import uuid

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from profiles.models import Profile


class RegisterForm(UserCreationForm):
    display_username = forms.CharField(
        label="Username",
        max_length=150,
        help_text=(
            "This is your visible NexTap username. "
            "Different customers may use the same one."
        ),
    )
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = [
            "display_username",
            "email",
            "password1",
            "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].widget.attrs.update(
            {
                "autocomplete": "email",
                "class": "form-control",
            }
        )
        self.fields["display_username"].widget.attrs.update(
            {
                "autocomplete": "nickname",
                "class": "form-control",
            }
        )
        for field_name in ("password1", "password2"):
            self.fields[field_name].widget.attrs.update(
                {
                    "autocomplete": "new-password",
                    "class": "form-control",
                }
            )

        self.fields["password1"].help_text = (
            "Use at least 8 characters. Uppercase letters and symbols "
            "are not required; very common passwords are not accepted."
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().casefold()

        if User.objects.filter(
            email__iexact=email
        ).exists() or Profile.objects.filter(
            login_email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = f"customer_{uuid.uuid4().hex}"
        user.email = self.cleaned_data["email"]

        if not commit:
            return user

        user.save()
        profile = user.profile
        profile.display_username = self.cleaned_data[
            "display_username"
        ].strip()
        profile.login_email = self.cleaned_data["email"]
        profile.email = self.cleaned_data["email"]
        profile.save(
            update_fields=[
                "display_username",
                "login_email",
                "email",
                "updated_at",
            ]
        )
        return user


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "class": "form-control",
            }
        ),
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "form-control",
            }
        ),
    )
