from django.http import HttpResponse
from django.utils.text import slugify
from django.db.models import Count
from rest_framework import generics, parsers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document, DocumentStatus
from apps.documents.serializers import (
    BatchDocumentUploadSerializer,
    DocumentDetailSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
)
from apps.documents.services import DocumentService


class DocumentUploadView(generics.GenericAPIView):
    serializer_class = DocumentUploadSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document, _task = DocumentService.create_document(
            owner=request.user,
            uploaded_file=serializer.validated_data["file"],
        )
        payload = DocumentSerializer(document).data
        return Response(payload, status=status.HTTP_202_ACCEPTED)


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return (
            Document.objects.filter(owner=self.request.user)
            .select_related("processing_task")
            .annotate(chunk_count=Count("chunks"))
        )


class DocumentDetailView(generics.RetrieveAPIView):
    serializer_class = DocumentDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            Document.objects.filter(owner=self.request.user)
            .select_related("processing_task")
            .annotate(chunk_count=Count("chunks"))
        )


class BatchDocumentUploadView(generics.GenericAPIView):
    serializer_class = BatchDocumentUploadSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accepted, rejected = DocumentService.create_documents_from_zip(
            owner=request.user,
            archive_file=serializer.validated_data["archive"],
        )

        documents = [document for document, _task in accepted]
        payload = DocumentSerializer(documents, many=True).data
        return Response(
            {
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
                "documents": payload,
                "errors": rejected,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DocumentResultDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        document = (
            Document.objects.filter(owner=request.user, id=id)
            .only("id", "original_filename", "status", "summary", "extracted_text", "processed_at")
            .first()
        )
        if not document:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        if document.status != DocumentStatus.PROCESSED:
            return Response(
                {"detail": "Document is not processed yet."},
                status=status.HTTP_409_CONFLICT,
            )

        safe_name = slugify(document.original_filename.rsplit(".", 1)[0]) or "document"
        response_content = (
            f"Document: {document.original_filename}\n"
            f"Processed At: {document.processed_at}\n\n"
            f"Summary\n"
            f"-------\n{document.summary}\n\n"
            f"Extracted Text\n"
            f"-------------\n{document.extracted_text}\n"
        )
        response = HttpResponse(response_content, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename=\"{safe_name}-processed.txt\"'
        return response
