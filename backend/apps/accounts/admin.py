from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import Module, Role, RolePermission, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "role", "is_active", "is_staff", "is_superuser", "last_login_at"]
    search_fields = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Role", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "last_login_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "role")}),
    )
    readonly_fields = ["last_login_at"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["key", "label"]


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ["role", "module", "action"]
    list_filter = ["role", "module", "action"]
