from io import BytesIO
import zipfile
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from apps.documents.models import Document, DocumentStatus
from apps.processing.models import ProcessingTask

User = get_user_model()


class DocumentAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="doc-user",
            email="doc-user@example.com",
            password="StrongPass123",
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": self.user.username, "password": "StrongPass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

    def test_upload_creates_document_and_processing_task(self):
        upload = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 test", content_type="application/pdf")

        response = self.client.post(reverse("document-upload"), {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Document.objects.count(), 1)
        document = Document.objects.get()
        self.assertEqual(document.status, DocumentStatus.PROCESSING)

        processing_task = ProcessingTask.objects.get(document=document)
        self.assertEqual(processing_task.celery_task_id, str(processing_task.id))

    @patch("apps.processing.tasks.process_document_task.apply_async")
    def test_upload_queues_task_after_commit(self, mock_apply_async):
        upload = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("document-upload"), {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(mock_apply_async.call_count, 1)

    def test_upload_rejects_invalid_extension(self):
        upload = SimpleUploadedFile("notes.txt", b"plain text", content_type="text/plain")
        response = self.client.post(reverse("document-upload"), {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only PDF and DOCX", str(response.data))

    def test_upload_rejects_invalid_pdf_signature(self):
        upload = SimpleUploadedFile("fake.pdf", b"not-a-pdf", content_type="application/pdf")
        response = self.client.post(reverse("document-upload"), {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid PDF signature", str(response.data))

    def test_list_returns_only_current_user_documents(self):
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="StrongPass123",
        )
        doc1 = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("mine.pdf", b"content", content_type="application/pdf"),
            original_filename="mine.pdf",
            content_type="application/pdf",
            file_size=7,
            status=DocumentStatus.PROCESSED,
        )
        Document.objects.create(
            owner=other_user,
            file=SimpleUploadedFile("other.pdf", b"content", content_type="application/pdf"),
            original_filename="other.pdf",
            content_type="application/pdf",
            file_size=7,
            status=DocumentStatus.PROCESSED,
        )

        response = self.client.get(reverse("document-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]["id"]), str(doc1.id))

    def test_batch_upload_accepts_supported_files(self):
        docx_stream = BytesIO()
        with zipfile.ZipFile(docx_stream, mode="w", compression=zipfile.ZIP_DEFLATED) as docx_archive:
            docx_archive.writestr("[Content_Types].xml", "<Types></Types>")
            docx_archive.writestr("word/document.xml", "<w:document></w:document>")
        docx_stream.seek(0)

        archive_stream = BytesIO()
        with zipfile.ZipFile(archive_stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("a.pdf", b"%PDF-1.4 test")
            archive.writestr("b.docx", docx_stream.read())
            archive.writestr("ignored.txt", b"plain text")
        archive_stream.seek(0)
        upload = SimpleUploadedFile("batch.zip", archive_stream.read(), content_type="application/zip")

        response = self.client.post(
            reverse("document-upload-batch"),
            {"archive": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["accepted_count"], 2)
        self.assertEqual(response.data["rejected_count"], 1)

    def test_download_processed_document_result(self):
        document = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("done.pdf", b"content", content_type="application/pdf"),
            original_filename="done.pdf",
            content_type="application/pdf",
            file_size=7,
            status=DocumentStatus.PROCESSED,
            summary="summary text",
            extracted_text="full extracted text",
        )

        response = self.client.get(reverse("document-download-result", kwargs={"id": document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("summary text", response.content.decode("utf-8"))

    @override_settings(UPLOADS_PER_MINUTE=1)
    def test_upload_rate_limit_blocks_excess_requests(self):
        first = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 first", content_type="application/pdf")
        second = SimpleUploadedFile("sample2.pdf", b"%PDF-1.4 second", content_type="application/pdf")

        first_response = self.client.post(reverse("document-upload"), {"file": first}, format="multipart")
        second_response = self.client.post(reverse("document-upload"), {"file": second}, format="multipart")

        self.assertEqual(first_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
