from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, DocumentStatus
from apps.processing.models import ProcessingTask

User = get_user_model()


class DocumentAPITests(APITestCase):
    def setUp(self):
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

    @patch("apps.processing.tasks.process_document_task.delay")
    def test_upload_creates_document_and_processing_task(self, mock_delay):
        mock_delay.return_value.id = "celery-test-id"
        upload = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 test", content_type="application/pdf")

        response = self.client.post(reverse("document-upload"), {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Document.objects.count(), 1)
        document = Document.objects.get()
        self.assertEqual(document.status, DocumentStatus.PROCESSING)

        processing_task = ProcessingTask.objects.get(document=document)
        self.assertEqual(processing_task.celery_task_id, "celery-test-id")

    def test_upload_rejects_invalid_extension(self):
        upload = SimpleUploadedFile("notes.txt", b"plain text", content_type="text/plain")
        response = self.client.post(reverse("document-upload"), {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only PDF and DOCX", str(response.data))

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
