from django import forms
from django.contrib import admin

from .models import NFCCard


class NFCCardAdminForm(forms.ModelForm):
    class Meta:
        model = NFCCard
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        representative = cleaned.get("representative")
        business = cleaned.get("business_profile")
        if representative and representative.business_id != getattr(business, "pk", None):
            self.add_error("representative", "Choose a representative from the selected business profile.")
        return cleaned


@admin.register(NFCCard)
class NFCCardAdmin(admin.ModelAdmin):
    form = NFCCardAdminForm
    list_display = (
        "card_uid",
        "owner",
        "business_profile",
        "representative",
        "status",
        "created_at",
        "programmed_at",
        "activated_at",
    )
    list_filter = ("status", "owner", "business_profile", "created_at", "programmed_at", "activated_at")
    search_fields = (
        "card_uid",
        "owner__username",
        "owner__email",
        "owner__profile__display_username",
        "owner__profile__full_name",
        "business_profile__name",
        "representative__name",
    )
    readonly_fields = (
        "card_uid",
        "public_token",
        "status",
        "created_at",
        "programmed_at",
        "programmed_by",
        "activated_at",
        "public_url_display",
        "assigned_order_display",
    )
    fieldsets = (
        ("Card identity", {"fields": ("card_uid", "public_token", "public_url_display", "status")}),
        ("Assignment", {"fields": ("owner", "business_profile", "representative", "assigned_order_display")}),
        ("Lifecycle history", {"fields": ("created_at", "programmed_at", "programmed_by", "activated_at")}),
    )

    @admin.display(description="Public profile URL")
    def public_url_display(self, obj):
        return obj.public_url if obj and obj.pk else "Generated when the card is saved"

    @admin.display(description="Assigned order")
    def assigned_order_display(self, obj):
        if not obj or not obj.pk:
            return "—"
        allocation = getattr(obj, "allocation", None)
        if allocation:
            return f"Order #{allocation.order_id} · Card {allocation.position}"
        order = getattr(obj, "assigned_order", None)
        return f"Order #{order.pk}" if order else "—"

    def save_model(self, request, obj, form, change):
        if change:
            obj.status = NFCCard.objects.get(pk=obj.pk).status
            super().save_model(request, obj, form, change)
            return

        created = NFCCard.create_with_generated_uid(
            owner=obj.owner,
            business_profile=obj.business_profile,
            representative=obj.representative,
            status="UNASSIGNED",
            programmed_at=None,
            programmed_by=None,
            activated_at=None,
        )
        obj.pk = created.pk
        obj.card_uid = created.card_uid
        obj.public_token = created.public_token
        obj.status = created.status
        obj.created_at = created.created_at

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.status != "UNASSIGNED":
            fields.extend(("owner", "business_profile", "representative"))
        return tuple(fields)

    def has_delete_permission(self, request, obj=None):
        # Keep existing Django delete permission behavior; no custom bulk action is added.
        return super().has_delete_permission(request, obj)
