import uuid

from django.db import models

from apps.documents.models import Document


class ProcessingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    STARTED = "STARTED", "Started"
    SUCCESS = "SUCCESS", "Success"
    FAILURE = "FAILURE", "Failure"


class ProcessingTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="processing_task",
    )
    status = models.CharField(
        max_length=16,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"{self.document_id} ({self.status})"
