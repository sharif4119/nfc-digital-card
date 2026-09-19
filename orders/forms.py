from django import forms

from .models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order

        fields = [
            "customer_name",
            "phone",
            "address",
            "city",
            "quantity",
        ]

        widgets = {
            "address": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

        self.fields["quantity"].widget.attrs.update(
            {
                "min": 1,
                "max": 5,
            }
        )

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]

        if quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least 1."
            )

        if quantity > 5:
            raise forms.ValidationError(
                "Maximum 5 cards per order."
            )

        return quantity

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()

        cleaned = (
            phone.replace("+", "")
            .replace("-", "")
            .replace(" ", "")
        )

        if not cleaned.isdigit():
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        if len(cleaned) < 10 or len(cleaned) > 15:
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        return phone