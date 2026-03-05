from django.contrib import admin

from apps.processing.models import ProcessingTask


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "status", "celery_task_id", "created_at", "completed_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "document__original_filename", "celery_task_id")
    readonly_fields = ("id", "created_at", "updated_at", "started_at", "completed_at")
