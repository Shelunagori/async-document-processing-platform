from django.urls import path

from apps.documents.views import (
    BatchDocumentUploadView,
    DocumentDetailView,
    DocumentListView,
    DocumentResultDownloadView,
    DocumentUploadView,
)

urlpatterns = [
    path("", DocumentListView.as_view(), name="document-list"),
    path("upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("upload-batch/", BatchDocumentUploadView.as_view(), name="document-upload-batch"),
    path("<uuid:id>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:id>/download/", DocumentResultDownloadView.as_view(), name="document-download-result"),
]
