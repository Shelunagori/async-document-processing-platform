import mimetypes
import zipfile
from pathlib import Path

import structlog
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

from apps.documents.models import Document, DocumentStatus
from apps.processing.models import ProcessingStatus, ProcessingTask

logger = structlog.get_logger(__name__)


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
            celery_task_id="",
        )
        processing_task.celery_task_id = str(processing_task.id)
        processing_task.save(update_fields=["celery_task_id", "updated_at"])

        from apps.processing.tasks import process_document_task

        def enqueue_processing_task() -> None:
            try:
                process_document_task.apply_async(
                    args=[str(document.id), str(processing_task.id)],
                    task_id=processing_task.celery_task_id,
                )
            except Exception as exc:  # pragma: no cover - network/broker failure
                logger.exception(
                    "processing_task_enqueue_failed",
                    document_id=str(document.id),
                    processing_task_id=str(processing_task.id),
                    error=str(exc),
                )
                ProcessingTask.objects.filter(id=processing_task.id).update(
                    status=ProcessingStatus.FAILURE,
                    error_message=f"Queue publish failed: {exc}",
                )
                Document.objects.filter(id=document.id).update(status=DocumentStatus.FAILED)

        transaction.on_commit(enqueue_processing_task)

        document.status = DocumentStatus.PROCESSING
        document.save(update_fields=["status", "updated_at"])
        return document, processing_task

    @staticmethod
    def get_file_extension(document: Document) -> str:
        return Path(document.original_filename).suffix.lower()

    @staticmethod
    def create_documents_from_zip(owner, archive_file) -> tuple[list[tuple[Document, ProcessingTask]], list[dict]]:
        from apps.documents.serializers import DocumentUploadSerializer

        accepted: list[tuple[Document, ProcessingTask]] = []
        rejected: list[dict] = []
        validator = DocumentUploadSerializer()

        archive_file.seek(0)
        with zipfile.ZipFile(archive_file) as zip_archive:
            entries = [entry for entry in zip_archive.infolist() if not entry.is_dir()]

            for entry in entries:
                filename = Path(entry.filename).name
                extension = Path(filename).suffix.lower()
                if not filename or extension not in {".pdf", ".docx"}:
                    rejected.append(
                        {
                            "filename": entry.filename,
                            "reason": "Unsupported file type in batch archive.",
                        }
                    )
                    continue

                if entry.file_size > settings.DOC_MAX_UPLOAD_SIZE:
                    rejected.append(
                        {
                            "filename": entry.filename,
                            "reason": "File exceeds per-document size limit.",
                        }
                    )
                    continue

                file_bytes = zip_archive.read(entry)
                guessed_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                upload = SimpleUploadedFile(
                    name=filename,
                    content=file_bytes,
                    content_type=guessed_type,
                )

                try:
                    validated_upload = validator.validate_file(upload)
                    document, task = DocumentService.create_document(
                        owner=owner,
                        uploaded_file=validated_upload,
                    )
                    accepted.append((document, task))
                except Exception as exc:
                    rejected.append(
                        {
                            "filename": entry.filename,
                            "reason": str(exc),
                        }
                    )

        return accepted, rejected
