from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import re

from .models import CardInquiry


class CardInquiryForm(forms.ModelForm):
    website_check = forms.CharField(required=False, widget=forms.HiddenInput)
    message = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "What would you like to know?"}),
    )
    contact_info = forms.CharField(
        max_length=254,
        label="Contact Information",
        widget=forms.TextInput(attrs={
            "placeholder": "Email, phone number or other contact",
            "autocomplete": "off",
        }),
    )

    class Meta:
        model = CardInquiry
        fields = ["name", "contact_info", "message"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Enter your name", "autocomplete": "name"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Your Name"
        self.fields["contact_info"].required = True
        self.fields["message"].required = True
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs["class"] = "form-control"

    def clean(self):
        data = super().clean()
        if data.get("website_check"):
            raise forms.ValidationError("Unable to submit this inquiry.")
        return data

    def clean_name(self):
        value = " ".join(self.cleaned_data["name"].split())
        if not any(character.isalnum() for character in value):
            raise forms.ValidationError("Enter a name containing letters or numbers.")
        return value

    def clean_contact_info(self):
        raw_value = self.cleaned_data["contact_info"]
        if any(ord(character) < 32 for character in raw_value):
            raise forms.ValidationError("Enter contact information on one line.")
        value = " ".join(raw_value.split())
        if len(value) < 3 or sum(character.isalnum() for character in value) < 2:
            raise forms.ValidationError("Enter a valid email, phone number or other contact.")
        return value

    def clean_message(self):
        value = self.cleaned_data["message"].strip()
        if not value or not any(character.isalnum() for character in value):
            raise forms.ValidationError("Enter a message so the business can respond.")
        return value

    @staticmethod
    def legacy_contact_fields(value):
        """Return conservative legacy phone/email values when input is recognizable."""
        try:
            validate_email(value)
            return {"email": value, "phone": ""}
        except ValidationError:
            pass
        digits = re.sub(r"[\s().-]", "", value)
        if re.fullmatch(r"\+?\d{7,15}", digits) and len(digits.lstrip("+")) <= 30:
            return {"phone": value[:30], "email": ""}
        return {"phone": "", "email": ""}
