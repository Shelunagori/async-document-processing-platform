from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("id", "username", "email", "is_staff", "is_active", "date_joined")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
