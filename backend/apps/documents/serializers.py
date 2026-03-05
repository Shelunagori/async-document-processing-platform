from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from apps.documents.models import Document

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        extension = Path(value.name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Only PDF and DOCX files are supported.")
        if value.size > settings.DOC_MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f"File too large. Max size is {settings.DOC_MAX_UPLOAD_SIZE} bytes."
            )
        return value


class DocumentSerializer(serializers.ModelSerializer):
    processing_task = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "original_filename",
            "content_type",
            "file_size",
            "status",
            "summary",
            "metadata",
            "created_at",
            "processed_at",
            "processing_task",
        )

    def get_processing_task(self, obj):
        task = getattr(obj, "processing_task", None)
        if not task:
            return None
        return {
            "id": task.id,
            "status": task.status,
            "celery_task_id": task.celery_task_id,
            "error_message": task.error_message,
        }


class DocumentDetailSerializer(DocumentSerializer):
    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields + (
            "extracted_text",
        )
