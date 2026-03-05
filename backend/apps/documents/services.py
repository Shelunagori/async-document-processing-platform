from pathlib import Path

from django.db import transaction

from apps.documents.models import Document, DocumentStatus
from apps.processing.models import ProcessingStatus, ProcessingTask


class DocumentService:
    @staticmethod
    @transaction.atomic
    def create_document(owner, uploaded_file) -> tuple[Document, ProcessingTask]:
        document = Document.objects.create(
            owner=owner,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            content_type=getattr(uploaded_file, "content_type", "application/octet-stream"),
            file_size=uploaded_file.size,
            status=DocumentStatus.UPLOADED,
        )
        processing_task = ProcessingTask.objects.create(
            document=document,
            status=ProcessingStatus.PENDING,
        )

        from apps.processing.tasks import process_document_task

        async_result = process_document_task.delay(str(document.id), str(processing_task.id))
        processing_task.celery_task_id = async_result.id
        processing_task.save(update_fields=["celery_task_id", "updated_at"])

        document.status = DocumentStatus.PROCESSING
        document.save(update_fields=["status", "updated_at"])
        return document, processing_task

    @staticmethod
    def get_file_extension(document: Document) -> str:
        return Path(document.original_filename).suffix.lower()
