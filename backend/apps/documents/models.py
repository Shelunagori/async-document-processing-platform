import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


class DocumentStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    PROCESSING = "PROCESSING", "Processing"
    PROCESSED = "PROCESSED", "Processed"
    FAILED = "FAILED", "Failed"


def document_upload_path(instance: "Document", filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"documents/{instance.owner_id}/{uuid.uuid4()}{suffix}"


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    file = models.FileField(upload_to=document_upload_path)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=127)
    file_size = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=16,
        choices=DocumentStatus.choices,
        default=DocumentStatus.UPLOADED,
        db_index=True,
    )
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"], name="doc_owner_status_idx"),
            models.Index(fields=["created_at"], name="doc_created_at_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.status})"


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    embedding = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_doc_chunk_index",
            )
        ]
        indexes = [
            models.Index(fields=["document", "chunk_index"], name="doc_chunk_lookup_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}:{self.chunk_index}"
