from __future__ import annotations

from time import perf_counter

import structlog
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.documents.models import DocumentChunk, DocumentStatus
from apps.processing.metrics import (
    documents_processed_total,
    failed_jobs_total,
    processing_time_seconds,
)
from apps.processing.models import ProcessingStatus, ProcessingTask
from pipeline.chunking import ChunkingStage
from pipeline.indexing import IndexingStage
from pipeline.ingestion import IngestionStage
from pipeline.metadata import MetadataStage
from pipeline.parsing import ParsingStage
from services.summary import DocumentSummaryService

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(), max_retries=0)
def process_document_task(self, document_id: str, processing_task_id: str) -> dict:
    task_start = perf_counter()

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

    stage_durations: dict[str, float] = {}

    try:
        ingestion_context = IngestionStage.prepare(document)

        stage_start = perf_counter()
        classification = ParsingStage.classify(
            ingestion_context.filename,
            ingestion_context.extension,
            ingestion_context.content_type,
        )
        stage_durations["classification"] = round(perf_counter() - stage_start, 4)

        stage_start = perf_counter()
        extracted_text = ParsingStage.extract_text(document.file.path, ingestion_context.extension)
        stage_durations["text_extraction"] = round(perf_counter() - stage_start, 4)

        stage_start = perf_counter()
        layout = ParsingStage.detect_layout(extracted_text)
        stage_durations["layout_detection"] = round(perf_counter() - stage_start, 4)

        stage_start = perf_counter()
        chunks = ChunkingStage.split_text(
            extracted_text,
            chunk_size=settings.PIPELINE_CHUNK_SIZE,
            overlap=settings.PIPELINE_CHUNK_OVERLAP,
        )
        stage_durations["chunking"] = round(perf_counter() - stage_start, 4)

        stage_start = perf_counter()
        chunk_records = IndexingStage.build_chunk_records(
            chunks,
            max_workers=settings.PIPELINE_CHUNK_PARALLELISM,
        )
        stage_durations["indexing"] = round(perf_counter() - stage_start, 4)

        stage_start = perf_counter()
        summary = DocumentSummaryService.generate_summary(extracted_text)
        stage_durations["summary_generation"] = round(perf_counter() - stage_start, 4)

        metadata = MetadataStage.build(
            extracted_text=extracted_text,
            summary=summary,
            classification=classification,
            layout=layout,
            chunks=chunks,
            stage_durations=stage_durations,
        )

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

            DocumentChunk.objects.filter(document=document).delete()
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        document=document,
                        chunk_index=record["chunk_index"],
                        content=record["content"],
                        embedding=record["embedding"],
                        metadata=record["metadata"],
                    )
                    for record in chunk_records
                ]
            )

            processing_task.refresh_from_db()
            processing_task.status = ProcessingStatus.SUCCESS
            processing_task.completed_at = timezone.now()
            processing_task.error_message = ""
            processing_task.save(
                update_fields=["status", "completed_at", "error_message", "updated_at"]
            )

        total_seconds = perf_counter() - task_start
        processing_time_seconds.observe(total_seconds)
        documents_processed_total.labels(result="success").inc()

        logger.info(
            "document_pipeline_completed",
            job_id=processing_task_id,
            document_id=document_id,
            duration=round(total_seconds, 4),
            stage_durations=stage_durations,
            chunk_count=len(chunk_records),
            classification=classification,
        )

    except Exception as exc:  # pragma: no cover - exercised by tests via mocks
        total_seconds = perf_counter() - task_start
        processing_time_seconds.observe(total_seconds)
        documents_processed_total.labels(result="failure").inc()
        failed_jobs_total.inc()

        logger.exception(
            "document_pipeline_failed",
            job_id=processing_task_id,
            document_id=document_id,
            duration=round(total_seconds, 4),
            stage_durations=stage_durations,
        )
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
