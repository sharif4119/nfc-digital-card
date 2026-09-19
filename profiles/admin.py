from django.contrib import admin

from .models import Profile


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