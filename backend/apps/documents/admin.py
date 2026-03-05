from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "owner", "status", "created_at", "processed_at")
    list_filter = ("status", "created_at")
    search_fields = ("original_filename", "owner__username", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at", "processed_at")
