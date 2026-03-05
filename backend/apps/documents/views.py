from rest_framework import generics, parsers, status
from rest_framework.response import Response

from apps.documents.models import Document
from apps.documents.serializers import (
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
        return Document.objects.filter(owner=self.request.user).select_related("processing_task")


class DocumentDetailView(generics.RetrieveAPIView):
    serializer_class = DocumentDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user).select_related("processing_task")
