from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from profiles.models import BusinessProfile, Profile

admin.site.unregister(User)


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    can_delete = False


class BusinessProfileInline(admin.StackedInline):
    model = BusinessProfile
    extra = 0
    can_delete = False


class NexTapUserChangeForm(UserChangeForm):
    def clean(self):
        cleaned = super().clean()
        user = self.instance
        if user.pk and user.is_superuser:
            last_active_superuser = not User.objects.filter(
                is_superuser=True, is_active=True
            ).exclude(pk=user.pk).exists()
            if last_active_superuser and (
                not cleaned.get("is_active", user.is_active)
                or not cleaned.get("is_superuser", user.is_superuser)
            ):
                raise ValidationError("The last active superuser cannot be deactivated or demoted.")
        return cleaned


@admin.register(User)
class NexTapUserAdmin(DjangoUserAdmin):
    form = NexTapUserChangeForm
    list_display = ("username", "display_name", "email", "is_active", "is_staff", "is_superuser")
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("username", "email", "profile__display_username", "profile__full_name")
    list_select_related = ("profile",)
    ordering = ("username",)
    inlines = (ProfileInline, BusinessProfileInline)

    def display_name(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.display_username or profile.full_name if profile else ""
    display_name.short_description = "Display name"

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return fieldsets
        filtered = []
        for title, options in fieldsets:
            fields = list(options.get("fields", ()))
            fields = [field for field in fields if field not in {"password", "last_login"}]
            if not request.user.is_superuser:
                fields = [field for field in fields if field not in {
                    "is_staff", "is_superuser", "groups", "user_permissions",
                }]
            if fields:
                filtered.append((title, {**options, "fields": fields}))
        return filtered

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and not request.user.is_superuser:
            for field in ("is_staff", "is_superuser", "groups", "user_permissions"):
                form.base_fields.pop(field, None)
        return form

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile")

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Individual deletion remains available when it cannot remove the
        # final active superuser; bulk deletion cannot safely enforce that.
        actions.pop("delete_selected", None)
        return actions

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_superuser and not User.objects.filter(
            is_superuser=True, is_active=True
        ).exclude(pk=obj.pk).exists():
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            fields.extend(field for field in ("is_staff", "is_superuser") if not request.user.is_superuser)
        return tuple(dict.fromkeys(fields))
