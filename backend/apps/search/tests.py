from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import Document, DocumentChunk, DocumentStatus

User = get_user_model()


class SearchAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="search-user",
            email="search-user@example.com",
            password="StrongPass123",
        )
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": self.user.username, "password": "StrongPass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

    def test_search_processed_documents(self):
        document = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("report.pdf", b"pdf", content_type="application/pdf"),
            original_filename="report.pdf",
            content_type="application/pdf",
            file_size=3,
            status=DocumentStatus.PROCESSED,
            extracted_text="Incident report about service degradation and mitigation details.",
            summary="Service degradation summary.",
        )
        DocumentChunk.objects.create(
            document=document,
            chunk_index=0,
            content="degradation happened in the payment service and was mitigated quickly",
            embedding=[0.1, 0.2],
            metadata={"word_count": 10},
        )

        response = self.client.get(reverse("document-search"), {"q": "degradation"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["original_filename"], "report.pdf")
        self.assertEqual(response.data["results"][0]["match_source"], "chunk")

    def test_search_requires_query_parameter(self):
        response = self.client.get(reverse("document-search"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("required", response.data["detail"])
