import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, DocumentStatus
from apps.processing.models import ProcessingStatus, ProcessingTask
from apps.processing.tasks import process_document_task

User = get_user_model()


class ProcessingTaskTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="proc-user",
            email="proc-user@example.com",
            password="StrongPass123",
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": self.user.username, "password": "StrongPass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

    def _create_document_and_task(self):
        document = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("sample.docx", b"docx-placeholder", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            original_filename="sample.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=17,
            status=DocumentStatus.PROCESSING,
        )
        task = ProcessingTask.objects.create(document=document, status=ProcessingStatus.PENDING)
        return document, task

    @patch("services.summary.DocumentSummaryService.generate_summary", return_value="Short summary.")
    @patch("services.extraction.DocumentExtractionService.extract_text", return_value="Sentence one. Sentence two. Sentence three.")
    def test_processing_task_success(self, mock_extract, mock_summary):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with override_settings(MEDIA_ROOT=tmp_dir):
                document, task = self._create_document_and_task()
                result = process_document_task(str(document.id), str(task.id))

                document.refresh_from_db()
                task.refresh_from_db()

        self.assertEqual(result["status"], ProcessingStatus.SUCCESS)
        self.assertEqual(document.status, DocumentStatus.PROCESSED)
        self.assertEqual(document.summary, "Short summary.")
        self.assertEqual(task.status, ProcessingStatus.SUCCESS)
        mock_extract.assert_called_once()
        mock_summary.assert_called_once()

    @patch("services.extraction.DocumentExtractionService.extract_text", side_effect=ValueError("Invalid file"))
    def test_processing_task_failure_marks_records(self, _mock_extract):
        document, task = self._create_document_and_task()

        with self.assertRaises(ValueError):
            process_document_task(str(document.id), str(task.id))

        document.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.FAILED)
        self.assertEqual(task.status, ProcessingStatus.FAILURE)
        self.assertIn("Invalid file", task.error_message)

    def test_task_status_endpoint(self):
        document, task = self._create_document_and_task()
        url = reverse("processing-task-detail", kwargs={"id": task.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ProcessingStatus.PENDING)
        self.assertEqual(str(response.data["document"]), str(document.id))
