from django.contrib import admin

from .models import BusinessProfile, BusinessRepresentative, FeaturedOffering, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "full_name",
        "company",
        "phone",
        "updated_at",
    ]

    search_fields = [
        "full_name",
        "user__username",
        "email",
        "phone",
    ]


class BusinessRepresentativeInline(admin.TabularInline):
    model = BusinessRepresentative
    extra = 0


class FeaturedOfferingInline(admin.TabularInline):
    model = FeaturedOffering
    extra = 0


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "profile_type", "organization_category", "updated_at")
    list_filter = ("profile_type", "organization_category", "show_owner_identity", "updated_at")
    search_fields = ("name", "owner__username", "owner__email", "owner__profile__full_name")
    readonly_fields = ("created_at", "updated_at")
    inlines = (BusinessRepresentativeInline, FeaturedOfferingInline)


@admin.register(BusinessRepresentative)
class BusinessRepresentativeAdmin(admin.ModelAdmin):
    list_display = ("name", "designation", "business", "phone_public", "email_public")
    list_filter = ("phone_public", "email_public")
    search_fields = ("name", "designation", "business__name")


@admin.register(FeaturedOffering)
class FeaturedOfferingAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "price", "position")
    search_fields = ("name", "business__name", "description")
