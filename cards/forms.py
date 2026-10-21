from django import forms

from .models import CardInquiry


class CardInquiryForm(forms.ModelForm):
    website_check = forms.CharField(required=False, widget=forms.HiddenInput)
    consent = forms.BooleanField(label="I agree to share these details with this business so they can respond to my inquiry.")

    class Meta:
        model = CardInquiry
        fields = ["name", "phone", "email", "interest", "message", "consent"]
        widgets = {"message": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                field.widget.attrs["class"] = "form-control"

    def clean(self):
        data = super().clean()
        if not data.get("phone") and not data.get("email"):
            raise forms.ValidationError("Provide a phone number or email so the business can reply.")
        if data.get("website_check"):
            raise forms.ValidationError("Unable to submit this inquiry.")
        return data
