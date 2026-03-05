from django.contrib import admin

from apps.documents.models import Document, DocumentChunk


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    readonly_fields = ("chunk_index", "content", "embedding", "metadata", "created_at")
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "owner", "status", "created_at", "processed_at")
    list_filter = ("status", "created_at")
    search_fields = ("original_filename", "owner__username", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at", "processed_at")
    inlines = (DocumentChunkInline,)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "chunk_index", "created_at")
    search_fields = ("document__original_filename", "content")
    readonly_fields = ("created_at",)
