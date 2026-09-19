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