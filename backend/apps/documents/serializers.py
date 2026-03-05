from pathlib import Path
import zipfile

from django.conf import settings
from rest_framework import serializers

from apps.documents.models import Document

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _validate_pdf_signature(uploaded_file) -> None:
    current_pos = uploaded_file.tell()
    uploaded_file.seek(0)
    header = uploaded_file.read(5)
    uploaded_file.seek(current_pos)
    if header != b"%PDF-":
        raise serializers.ValidationError("Invalid PDF signature.")


def _validate_zip_compression_safety(archive: zipfile.ZipFile, max_uncompressed: int, max_ratio: int) -> None:
    total_uncompressed = 0
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        total_uncompressed += entry.file_size
        if total_uncompressed > max_uncompressed:
            raise serializers.ValidationError("Archive exceeds safe uncompressed size limit.")

        if entry.compress_size > 0:
            ratio = entry.file_size / entry.compress_size
            if ratio > max_ratio:
                raise serializers.ValidationError("Archive appears to have unsafe compression ratio.")


def _validate_docx_signature_and_safety(uploaded_file) -> None:
    current_pos = uploaded_file.tell()
    uploaded_file.seek(0)

    if not zipfile.is_zipfile(uploaded_file):
        uploaded_file.seek(current_pos)
        raise serializers.ValidationError("Invalid DOCX archive.")

    uploaded_file.seek(0)
    with zipfile.ZipFile(uploaded_file) as archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            uploaded_file.seek(current_pos)
            raise serializers.ValidationError("Invalid DOCX structure.")
        _validate_zip_compression_safety(
            archive,
            max_uncompressed=settings.DOCX_MAX_UNCOMPRESSED_SIZE,
            max_ratio=settings.DOCX_MAX_COMPRESSION_RATIO,
        )

    uploaded_file.seek(current_pos)


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

        allowed_mimes = settings.DOC_ALLOWED_MIME_TYPES.get(extension, set())
        if allowed_mimes and getattr(value, "content_type", None) not in allowed_mimes:
            raise serializers.ValidationError("Unsupported MIME type for the uploaded file.")

        if extension == ".pdf":
            _validate_pdf_signature(value)
        elif extension == ".docx":
            _validate_docx_signature_and_safety(value)

        return value


class BatchDocumentUploadSerializer(serializers.Serializer):
    archive = serializers.FileField()

    def validate_archive(self, value):
        extension = Path(value.name).suffix.lower()
        if extension != ".zip":
            raise serializers.ValidationError("Only ZIP archives are supported for batch upload.")
        if value.size > settings.BATCH_MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f"Batch file too large. Max size is {settings.BATCH_MAX_UPLOAD_SIZE} bytes."
            )

        current_pos = value.tell()
        value.seek(0)
        if not zipfile.is_zipfile(value):
            value.seek(current_pos)
            raise serializers.ValidationError("Invalid ZIP archive.")

        value.seek(0)
        with zipfile.ZipFile(value) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            if not entries:
                value.seek(current_pos)
                raise serializers.ValidationError("ZIP archive does not contain files.")
            if len(entries) > settings.BATCH_MAX_FILES:
                value.seek(current_pos)
                raise serializers.ValidationError(
                    f"Too many files in archive. Max is {settings.BATCH_MAX_FILES}."
                )
            _validate_zip_compression_safety(
                archive,
                max_uncompressed=settings.BATCH_MAX_UNCOMPRESSED_SIZE,
                max_ratio=settings.DOCX_MAX_COMPRESSION_RATIO,
            )

        value.seek(current_pos)
        return value


class DocumentSerializer(serializers.ModelSerializer):
    processing_task = serializers.SerializerMethodField()
    chunk_count = serializers.SerializerMethodField()

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
            "chunk_count",
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

    def get_chunk_count(self, obj):
        if hasattr(obj, "chunk_count"):
            return obj.chunk_count
        return obj.chunks.count()


class DocumentDetailSerializer(DocumentSerializer):
    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields + (
            "extracted_text",
        )
