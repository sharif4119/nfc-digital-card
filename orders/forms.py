from django import forms

from .models import Order


class OrderForm(forms.ModelForm):
    business_order_type = forms.ChoiceField(
        choices=[("SINGLE", "Single business card"), ("MULTIPLE", "Multiple business cards")],
        required=False,
    )
    quantity = forms.IntegerField(min_value=1, max_value=25, required=False)

    class Meta:
        model = Order

        fields = [
            "customer_name",
            "phone",
            "address",
            "city",
            "business_order_type",
            "quantity",
        ]

        widgets = {
            "address": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        if product is None or product.card_category != "BUSINESS":
            self.fields.pop("business_order_type")
            self.fields.pop("quantity")
        else:
            self.fields["business_order_type"].required = True
            self.fields["quantity"].required = True
            self.fields["quantity"].initial = 1

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

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

    def clean(self):
        cleaned = super().clean()
        if self.product and self.product.card_category == "BUSINESS":
            kind = cleaned.get("business_order_type")
            quantity = cleaned.get("quantity")
            if kind == "SINGLE" and quantity != 1:
                self.add_error("quantity", "A single business card order must contain one card.")
            if kind == "MULTIPLE" and quantity is not None and quantity < 2:
                self.add_error("quantity", "Choose at least two cards for a multiple-card order.")
        return cleaned
