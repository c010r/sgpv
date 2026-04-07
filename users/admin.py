from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rol", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff", "is_active")
