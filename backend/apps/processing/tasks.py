from __future__ import annotations

import logging
from pathlib import Path

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.documents.models import DocumentStatus
from apps.processing.models import ProcessingStatus, ProcessingTask
from services.extraction import DocumentExtractionService
from services.summary import DocumentSummaryService

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(), max_retries=0)
def process_document_task(self, document_id: str, processing_task_id: str) -> dict:
    with transaction.atomic():
        processing_task = ProcessingTask.objects.select_related("document").select_for_update().get(
            id=processing_task_id
        )
        processing_task.status = ProcessingStatus.STARTED
        processing_task.started_at = timezone.now()
        processing_task.save(update_fields=["status", "started_at", "updated_at"])

        document = processing_task.document
        document.status = DocumentStatus.PROCESSING
        document.save(update_fields=["status", "updated_at"])

    try:
        file_extension = Path(document.original_filename).suffix.lower()
        extracted_text = DocumentExtractionService.extract_text(document.file.path, file_extension)
        summary = DocumentSummaryService.generate_summary(extracted_text)
        metadata = {
            "word_count": len(extracted_text.split()),
            "character_count": len(extracted_text),
            "summary_length": len(summary),
        }

        with transaction.atomic():
            document.refresh_from_db()
            document.extracted_text = extracted_text
            document.summary = summary
            document.metadata = metadata
            document.status = DocumentStatus.PROCESSED
            document.processed_at = timezone.now()
            document.save(
                update_fields=[
                    "extracted_text",
                    "summary",
                    "metadata",
                    "status",
                    "processed_at",
                    "updated_at",
                ]
            )

            processing_task.refresh_from_db()
            processing_task.status = ProcessingStatus.SUCCESS
            processing_task.completed_at = timezone.now()
            processing_task.error_message = ""
            processing_task.save(
                update_fields=["status", "completed_at", "error_message", "updated_at"]
            )

    except Exception as exc:  # pragma: no cover - exercised by tests via mocks
        logger.exception("Document processing failed", extra={"document_id": document_id})
        with transaction.atomic():
            document.refresh_from_db()
            document.status = DocumentStatus.FAILED
            document.save(update_fields=["status", "updated_at"])

            processing_task.refresh_from_db()
            processing_task.status = ProcessingStatus.FAILURE
            processing_task.completed_at = timezone.now()
            processing_task.error_message = str(exc)
            processing_task.save(
                update_fields=["status", "completed_at", "error_message", "updated_at"]
            )
        raise

    return {
        "document_id": document_id,
        "processing_task_id": processing_task_id,
        "status": ProcessingStatus.SUCCESS,
    }
